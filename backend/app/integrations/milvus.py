from threading import Lock

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.integrations.model_runtime import get_model_runtime


class MilvusIndex:
    _lock = Lock()

    def __init__(self):
        self.settings = get_settings()
        self.model_config = get_model_runtime().config()
        self.alias = "edu_agent"

    def connect(self) -> None:
        if not connections.has_connection(self.alias):
            connections.connect(
                alias=self.alias, host=self.settings.milvus_host, port=str(self.settings.milvus_port)
            )

    def collection(self) -> Collection:
        self.connect()
        name = self.model_config.vector_collection
        with self._lock:
            if not utility.has_collection(name, using=self.alias):
                schema = CollectionSchema(
                    fields=[
                        FieldSchema("id", DataType.VARCHAR, max_length=64, is_primary=True),
                        FieldSchema("chunk_id", DataType.INT64),
                        FieldSchema("course_id", DataType.INT64),
                        FieldSchema("document_id", DataType.INT64),
                        FieldSchema("category", DataType.VARCHAR, max_length=80),
                        FieldSchema("content_hash", DataType.VARCHAR, max_length=64),
                        FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=self.model_config.embedding_dimension),
                    ],
                    description="AI education document chunks",
                    enable_dynamic_field=False,
                )
                collection = Collection(name, schema=schema, using=self.alias)
                collection.create_index(
                    "embedding", {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}}
                )
            else:
                collection = Collection(name, using=self.alias)
                embedding_field = next(field for field in collection.schema.fields if field.name == "embedding")
                actual_dimension = int(embedding_field.params.get("dim", 0))
                if actual_dimension != self.model_config.embedding_dimension:
                    raise AppError(
                        "MILVUS_DIMENSION_MISMATCH",
                        f"collection {name} 的维度为 {actual_dimension}，当前 Embedding 配置为 "
                        f"{self.model_config.embedding_dimension}；请使用新的 collection 名称或重建向量索引",
                        409,
                    )
        collection.load()
        return collection

    def upsert(self, rows: list[dict]) -> None:
        if not rows:
            return
        collection = self.collection()
        ids = [str(row["chunk_id"]) for row in rows]
        escaped = ",".join(f'"{value}"' for value in ids)
        collection.delete(f"id in [{escaped}]")
        collection.insert(
            [
                ids,
                [row["chunk_id"] for row in rows],
                [row["course_id"] for row in rows],
                [row["document_id"] for row in rows],
                [row["category"] for row in rows],
                [row["content_hash"] for row in rows],
                [row["embedding"] for row in rows],
            ]
        )
        collection.flush()

    def search(self, embedding: list[float], course_id: int, top_k: int) -> list[tuple[int, float]]:
        results = self.collection().search(
            data=[embedding], anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"ef": max(64, top_k * 4)}},
            limit=top_k, expr=f"course_id == {int(course_id)}", output_fields=["chunk_id"],
        )
        return [(int(hit.entity.get("chunk_id")), float(hit.score)) for hit in results[0]]

    def delete_document(self, document_id: int) -> None:
        collection = self.collection()
        collection.delete(f"document_id == {int(document_id)}")
        collection.flush()

    def health(self) -> dict:
        self.connect()
        return {"ok": True, "collection": self.model_config.vector_collection,
                "dimension": self.model_config.embedding_dimension,
                "collections": utility.list_collections(using=self.alias)}
