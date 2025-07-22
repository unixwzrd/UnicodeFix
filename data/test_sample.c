// “Sample” C file — with EM dash
#include <stdio.h>

// Function with EN dash – and non-breaking hyphen ‑
void hello_world() {
    printf("Hello, world!\n"); // “Hello” with smart quotes
    printf("Hyphen-minus: -\n");
    printf("Non-breaking hyphen: ‑\n");
    printf("EN dash: –\n");
    printf("EM dash: —\n");
    printf("Zero-width space:\u200b\n"); // Should be removed
    printf("Trailing whitespace here...   \n");
}

int main() {
    hello_world();
    return 0;
} 