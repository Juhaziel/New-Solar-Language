package frontend.lexer;

/**
 * Represents a keyword token in the Token stream.
 */
public class TkKeyword extends Token {
    /**
     * Represents a New Solar keyword.
     */
    public static enum NSKeyword {
        DECLARE,
        STATIC,
        VAR, FUN,
        STRUCT, UNION, USING,
        VOLATILE, LONE,
        INT16, INT32,
        VOID,
        TYPEOF,
        IF, ELSE, WHILE, FOR,
        CONTINUE, BREAK, BREAKIF, RETURN
    }

    private NSKeyword keywordType;

    /**
     * Construct a Keyword token of the specified type.
     * 
     * @param keywordType the type of keyword
     */
    public TkKeyword(NSKeyword keywordType) {
        this.keywordType = keywordType;
    }

    /**
     * @return the NSKeyword associated with this TkKeyword.
     */
    public NSKeyword getKeywordType() {
        return keywordType;
    }

    /**
     * Returns true for memory-resident definition keywords which can take storage qualifiers and false otherwise.
     */
    public boolean isResidentDefinitionKeyword() {
        if (keywordType == NSKeyword.VAR || keywordType == NSKeyword.FUN)
            return true;

        return false;
    }

    /**
     * Returns true for storage qualifiers and false otherwise.
     */
    public boolean isStorageQualifier() {
        if (keywordType == NSKeyword.STATIC)
            return true;

        return false;
    }

    /**
     * Returns true for type definition keywords and false otherwise.
     */
    public boolean isTypeDefinitionKeyword() {
        if (keywordType == NSKeyword.STRUCT ||
            keywordType == NSKeyword.UNION ||
            keywordType == NSKeyword.USING)
                return true;

        return false;
    }
    
    /**
     * Returns true for fixed type keywords which can take type qualifiers and false otherwise.
     */
    public boolean isFixedType() {
        if (keywordType == NSKeyword.INT16 ||
            keywordType == NSKeyword.INT32 ||
            keywordType == NSKeyword.VOID ||
            keywordType == NSKeyword.TYPEOF)
                return true;
        
        return false;
    }


    /**
     * Returns true for type qualifiers and false otherwise.
     */
    public boolean isTypeQualifier() {
        if (keywordType == NSKeyword.VOLATILE ||
            keywordType == NSKeyword.LONE)
                return true;
        
        return false;
    }

    /**
     * Returns true for conditional control flow keywords that can take labels and else statements and false otherwise.
     */
    public boolean isConditionalControlFlow() {
        if (keywordType == NSKeyword.IF ||
            keywordType == NSKeyword.WHILE ||
            keywordType == NSKeyword.FOR)
                return true;
        
        return false;
    }

    /**
     * Returns true for jump keywords that can take labels and false otherwise.
     */
    public boolean isJump() {
        if (keywordType == NSKeyword.IF ||
            keywordType == NSKeyword.WHILE ||
            keywordType == NSKeyword.FOR)
                return true;
        
        return false;
    }

    /**
     * Returns true for continue keyword that can take labels and false otherwise.
     */
    public boolean isContinue() {
        if (keywordType == NSKeyword.IF ||
            keywordType == NSKeyword.WHILE ||
            keywordType == NSKeyword.FOR)
                return true;
        
        return false;
    }

    /**
     * Returns true for break and breakif keyword that can take labels and false otherwise.
     */
    public boolean isBreak() {
        if (keywordType == NSKeyword.IF ||
            keywordType == NSKeyword.WHILE ||
            keywordType == NSKeyword.FOR)
                return true;
        
        return false;
    }

    public String toString() {
        return String.format("<Keyword: '%1'>", this.keywordType.toString().toLowerCase());
    }
}
