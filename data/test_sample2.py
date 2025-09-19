# “Sample” Python file — with EM dash
# This file is for testing Unicode and whitespace cleanup.


def greet(name):    
    print(f"Hello, {name}!")  # “Hello” with smart quotes
    print('Goodbye — world!')  # EM dash
    print('Hyphen-minus: -')
    print('Non-breaking hyphen: ‑')
    print('EN dash: –')
    print('EM dash: —')
    print('Zero-width space:')  # Should be removed

    

def add(a, b):
    # Adds two numbers – with EN dash
    return a + b  


def main():
    greet("Alice")
    result = add(5, 7)
    print(f"Result: {result}")
    # Call greet again with EM dash — and EN dash –
    greet('Bob')

    
if __name__ == '__main__':
    main() 