package frontend.lexer;

/**
 * Represents the end of file in a Token stream.
 */
public class TkEof extends Token {
    public String toString() {
        return "<EOF>";
    }
}
