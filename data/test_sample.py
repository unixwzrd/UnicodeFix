# This is a sample Python file — with EM dash
# Here’s a function with smart quotes and EN dash – and non-breaking hyphen ‑
def hello_world():
    print("Hello, world!")  # “Hello” with smart quotes
    print('Goodbye — world!')  # EM dash
    print('Hyphen-minus: -')
    print('Non-breaking hyphen: ‑')
    print('EN dash: –')
    print('EM dash: —')
    print('Zero-width space:')  # Should be removed
    print('Trailing whitespace here...   ')

if __name__ == '__main__':
    hello_world() 