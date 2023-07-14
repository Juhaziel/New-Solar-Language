package frontend.lexer;

/**
 * Represents an identifier token in the Token stream.
 */
public class TkName extends Token {
    private String name;

    public String toString() {
        return String.format("<Name: '%1'>", name);
    }
}
