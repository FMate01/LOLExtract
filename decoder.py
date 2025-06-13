class Decoder:
    def decompress(self, raw_data: bytes, file_path: str = None) ->None:
        """
        Decompresses the given data.
        
        :param data: The compressed data to decompress.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")