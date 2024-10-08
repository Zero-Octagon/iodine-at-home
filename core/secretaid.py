import sys

def encrypt_mapping(mapping):
    encrypted_mapping = {}
    for key, value in mapping.items():
        encrypted_key = chr(ord(key) + 3)
        encrypted_value = '*' + ''.join(chr(ord(char) + 3) for char in value) + '#'
        encrypted_mapping[encrypted_key] = encrypted_value
    return encrypted_mapping

def decrypt_mapping(encrypted_mapping):
    decrypted_mapping = {}
    for key, value in encrypted_mapping.items():
        decrypted_key = chr(ord(key) - 3)
        decrypted_value = ''.join(chr(ord(char) - 3) for char in value[1:-1])  # 去掉符号
        decrypted_mapping[decrypted_key] = decrypted_value
    return decrypted_mapping

original_mapping = {
    'A': 'Q',
    'B': 'C',
    'C': 'A',
    'D': 'B',
    'E': '@',
    'F': '%',
    'G': 'P',
    'H': 'Q',
    'I': 'L',
    'J': 'K',
    'K': 'P',
    'L': 'M',
    'M': 'Q',
    'N': 'A',
    'O': 'C',
    'P': 'P',
    'Q': 'F',
    'R': 'S',
    'S': 'T',
    'T': 'Z',
    'U': 'W',
    'V': '!@#',
    'W': '%$#',
    'X': '89',
    'Y': '18',
    'Z': '42',
    'a': 'q',
    'b': 'c',
    'c': 'a',
    'd': 'b',
    'e': '@',
    'f': '%',
    'g': 'p',
    'h': 'q',
    'i': 'l',
    'j': 'k',
    'k': 'p',
    'l': 'm',
    'm': 'q',
    'n': 'a',
    'o': 'c',
    'p': 'p',
    'q': 'f',
    'r': 's',
    's': 't',
    't': 'z',
    'u': 'w',
    'v': '!@#',
    'w': '%$#',
    'x': '89',
    'y': '18',
    'z': '42'
}

# 加密和解密
encrypted_mapping = encrypt_mapping(original_mapping)

# 用户输入ID部分
user_input = input("ID: ")

# 解密映射
decrypted_mapping = decrypt_mapping(encrypted_mapping)

output = []
for char in user_input:
    if char in decrypted_mapping:
        output.append(decrypted_mapping[char])
    else:
        output.append(char)

# 输出ID的解密结果
print('EncodeID:', ''.join(output).encode('gbk', errors='replace').decode('gbk'))

# 再次加密原始映射
encrypted_mapping = encrypt_mapping(original_mapping)

# 用户输入secret部分
user_input = input("secret: ")

# 解密映射
decrypted_mapping = decrypt_mapping(encrypted_mapping)

output = []
for char in user_input:
    if char in decrypted_mapping:
        output.append(decrypted_mapping[char])
    else:
        output.append(char)

# 输出secret的解密结果
print('EncodeSecret:', ''.join(output).encode('gbk', errors='replace').decode('gbk'))
