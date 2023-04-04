import sys, os, io
import argparse

# Making sure we're fetching the right stuff here
compiler_dir = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, compiler_dir)
import internals.nslex as nslex
import internals.nsparse as nsparse
import internals.nslog as nslog
import internals.nsstbuilder as nsst

# Get Compiler logger
complogger = nslog.LoggerFactory.getLogger()

# Setting up the argument parser
argparser = argparse.ArgumentParser(
    description="Compiles source files written in New Solar (*.ns) to Mercury Assembly.")
group = argparser.add_mutually_exclusive_group()
group.add_argument("--debug", action="store_true", help="show debug output", default=False)
group.add_argument("-v", "--verbose", action="store_true", help="show verbose output", default=False)
group.add_argument("-woff", "--no-warnings", action="store_true", help="show only errors", default=False)
argparser.add_argument("-f", action="extend", nargs="+", dest="options", help="specify options for the compiler", default=[])
argparser.add_argument("-d", "--dir", help="specify the output directory for the output files", default=os.getcwd())
argparser.add_argument("infile", action="extend", nargs=argparse.REMAINDER, help="specify the New Solar files to compile", default=[])
argparser.parse_args()   

# Actual compilation
def main(args):
    success=True
    for infile in args.infile:
        print(f"\n-- in \"{infile}\"")
        
        # Get the source file contents
        with open(infile, "r", encoding="utf-8") as f:
            insource = f.read()
        
        # Lex the source file
        try:
            complogger.resetpad()
            lexer = nslex.Lexer(insource)
            tokens = lexer.lex_all()
            if not lexer.success:
                success = False
                continue
            else: complogger.info("lexer phase succeeded.")
        except Exception as e:
            complogger.fatal(f"Lexer threw uncaught exception with message: {e}")
            success = False
            continue
        del lexer
        
        # Parse the source file
        try:
            complogger.resetpad()
            parser = nsparse.Parser(tokens)
            ast = parser.parse_module()
            if not parser.success:
                success = False
                continue
            else: complogger.info("parser phase succeeded.")
        except Exception as e:
            complogger.fatal(f"Parser threw uncaught exception with message: {e}")
            success = False
            continue
        del parser
        
        # Bake symbol table into AST
        try:
            complogger.resetpad()
            if not nsst.GenerateTable(ast):
                success = False
                continue
            else: complogger.info("symbol table builder phase succeeded.")
        except Exception as e:
            complogger.fatal(f"Symbol table builder threw uncaught exception with message: {e}")
            success = False
            continue
        
        # Semantic analysis and basic simplification
        try:
            complogger.resetpad()
            # TODO: Implement and call semantic analyser
            pass
        except Exception as e:
            complogger.fatal(f"Semantic analyser threw uncaught exception with message: {e}")
            success = False
            continue
        
        # Generate assembly code
        try:
            complogger.resetpad()
            # TODO: Implement and call code generator
            pass
        except Exception as e:
            complogger.fatal(f"Assembly generator threw uncaught exception with message: {e}")
            success = False
            continue
        
        complogger.info(f"successfully compiled \"{infile}\"")
    if success:
        print(f"[SUCCESS] compilation of {len(args.infile)} file(s) succeeded.")
    else:
        print(f"[FAILED] compilation of {len(args.infile)} file(s) failed.")

if __name__ == "__main__":
    args = argparser.parse_args()
    
    # Check infiles
    if not args.infile:
        complogger.fatal("must specify at least one input file.")
        exit(-1)
        
    for i, infile in enumerate(args.infile):
        if not os.path.isfile(infile):
            complogger.fatal(f"cannot find input file \"{infile}\"")
            exit(-1)
        args.infile[i] = os.path.relpath(infile, os.getcwd())
    
    # Check verbosity level
    if args.no_warnings:
        complogger.setLevel(nslog.LogLevel.ERROR)
    elif args.verbose:
        complogger.setLevel(nslog.LogLevel.INFO)
    elif args.debug:
        complogger.setLevel(nslog.LogLevel.DEBUG)
        
    complogger.debug(args)
    
    # Check output directory isn't file
    if os.path.exists(args.dir) and not os.path.isdir(args.dir):
        complogger.fatal(f"specified output path \"{args.dir}\" exists but is not a directory.")
        exit(-1)
    
    main(args)