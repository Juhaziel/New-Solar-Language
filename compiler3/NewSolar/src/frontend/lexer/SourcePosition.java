package frontend.lexer;

/** 
 * Data class representing a position in the source code.
 */
public class SourcePosition {
    /**
     * Constant representing a lack of position information for a particular field.
     */
    public static final int NONE = -1;

    private int srcLine;
    private int srcCol;
    private int endLine;
    private int endCol;

    /**
     * Constructs a 1-character wide SourcePosition.
     * 
     * @param sourceLine
     * @param sourceColumn
     */
    public SourcePosition(int sourceLine, int sourceColumn) {
        this(sourceLine, sourceColumn, sourceLine, sourceColumn);
    }

    /**
     * Constructs a SourcePosition that can span an arbitrary length.
     * 
     * @param startLine
     * @param startColumn
     * @param endLine
     * @param endColumn
     */
    public SourcePosition(int startLine, int startColumn, int endLine, int endColumn) {
        this.setStartPosition(startLine, startColumn);
        this.setEndPosition(endLine, endColumn);
    }

    /**
     * Sets the start line and column.
     * 
     * @param line
     * @param column
     * @return the SourcePosition itself for chained calls.
     */
    public SourcePosition setStartPosition(int line, int column) {
        this.srcLine = line;
        this.srcCol = column;

        return this;
    }

    /**
     * Sets the end line and column.
     * 
     * @param line
     * @param column
     * @return the SorucePosition itself for chained calls.
     */
    public SourcePosition setEndPosition(int line, int column) {
        this.endLine = line;
        this.endCol = column;

        return this;
    }

    /**
     * @return the start line
     */
    public int getStartLine() {
        return srcLine;
    }

    /**
     * @return the start column
     */
    public int getStartColumn() {
        return srcCol;
    }

    /**
     * @return the end line
     */
    public int getEndLine() {
        return endLine;
    }

    /**
     * @return the end column
     */
    public int getEndColumn() {
        return endCol;
    }
}
