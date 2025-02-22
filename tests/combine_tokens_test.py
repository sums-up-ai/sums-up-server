from app.services.post_processing.combine_tokens import CombineTokens

tokenizer = CombineTokens()

test1 = tokenizer.combine("ක්", "රි")
print(f"ක් + රි = {test1}")
print("Unicode:", [hex(ord(c)) for c in test1])

test2 = tokenizer.combine("ර්", "ක")
print(f"\nර් + ක = {test2}")
print("Unicode:", [hex(ord(c)) for c in test2])

test3 = tokenizer.combine("ම්", "ම")
print(f"\nම් + ම = {test3}")
print("Unicode:", [hex(ord(c)) for c in test3])

test4 = tokenizer.combine("ක්", "ව")
print(f"\nක් + ව = {test4}")
print("Unicode:", [hex(ord(c)) for c in test4])
