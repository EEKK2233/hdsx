class TextLoader:
    supported_encodings = ("utf-8-sig", "utf-8", "gb18030")

    def load(self, content: bytes) -> str:
        for encoding in self.supported_encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")

