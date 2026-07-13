from app.integrations.milvus import MilvusIndex


class MilvusVectorIndex(MilvusIndex):
    """RAG 领域层入口；底层连接实现继续由 integrations 负责。"""

