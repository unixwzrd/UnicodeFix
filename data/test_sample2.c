// “Sample” C file — with EM dash
#include <stdio.h>


void greet(const char* name) {
    printf("Hello, %s!\n", name); // “Hello” with smart quotes
    printf("Goodbye — world!\n"); // EM dash
    printf("Hyphen-minus: -\n");
    printf("Non-breaking hyphen: ‑\n");
    printf("EN dash: –\n");
    printf("EM dash: —\n");
    printf("Zero-width space:\u200b\n"); // Should be removed
    printf("Trailing whitespace here...   \n");
}


int add(int a, int b) {
    // Adds two numbers – with EN dash
    return a + b;    
}


int main() {
    greet("Alice");
    int result = add(5, 7);
    printf("Result: %d\n", result);
    // Call greet again with EM dash — and EN dash –
    greet("Bob");
    return 0;   
} 