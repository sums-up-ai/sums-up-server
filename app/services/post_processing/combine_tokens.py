class CombineTokens:
    def __init__(self):
        self.zwj = '\u200D'
        self.hal_kirima = '\u0DCA'  # ්
    
    def combine(self, token1: str, token2: str) -> str:

        if not token1 or not token2:
            return token1 + token2

        last_char = token1[-1]
        first_char = token2[0]
        
        combined = self._handle_hal_kirima(token1, token2)
        if combined is not None:
            return combined
            
        combined = self._handle_repaya(token1, token2)
        if combined is not None:
            return combined
            
        if self._is_touching_pair(token1, token2):
            return token1 + token2
            
        return token1 + token2

    def _handle_hal_kirima(self, token1, token2):
        if ord(token1[-1]) == 0x0DCA:
            next_char = token2[0]
            # Yansaya (් + ය)
            if next_char == 'ය':
                return token1 + self.zwj + token2
            # Rakaransaya (් + ර)
            if next_char == 'ර':
                return token1 + self.zwj + token2
            # Regular consonant clusters (ක්ව, ක්ෂ)
            return token1 + token2
        return None

    def _handle_repaya(self, token1, token2):
        """Handle repaya combinations (ර් + consonant)"""
        if token1.endswith('ර') and token2.startswith(self.hal_kirima):
            return token1 + self.zwj + token2
        return None

    def _is_touching_pair(self, token1, token2):
        """Check for special touching combinations"""
        touching_pairs = {
            'ක්ක', 'ච්ච', 'ජ්ජ', 'ත්ත', 'න්ද',
            'න්ධ', 'ප්ප', 'ම්ම', 'ක්ෂ', 'ක්ව'
        }
        pair = token1[-1] + token2[0]
        return pair in touching_pairs