package frontend.lexer;

public abstract class Token {
    private SourcePosition position;

    /**
     * Set the SourcePosition of this token.
     * 
     * @param sourcePosition
     */
    public void setSourcePosition(SourcePosition sourcePosition) {
        this.position = sourcePosition;
    }

    /**
     * @return the SourcePosition of this token.
     */
    public SourcePosition getSourcePosition() {
        return position;
    }

    public abstract String toString();
}
