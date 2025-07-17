import re
import os
import colorama # Import the colorama library
import sys      # Import the sys module to access command-line arguments

class ZCLILanguage:
    """
    Implements the ZCLI programming language interpreter and compiler.
    Supports defining variables, printing, comments, and file operations.
    """
    def __init__(self):
        # Initialize colorama for cross-platform ANSI support
        colorama.init()

        # Colorama's reset and foreground colors
        self.ANSI_RESET = colorama.Style.RESET_ALL
        self.ANSI_COLORS = {
            "red": colorama.Fore.RED,
            "orange": colorama.Fore.YELLOW, # Closest standard ANSI for orange
            "yellow": colorama.Fore.YELLOW,
            "green": colorama.Fore.GREEN,
            "blue": colorama.Fore.BLUE,
            "indigo": colorama.Fore.BLUE,   # Closest standard ANSI for indigo
            "violet": colorama.Fore.MAGENTA, # Closest standard ANSI for violet
            # Additional common colors for convenience
            "purple": colorama.Fore.MAGENTA,
            "cyan": colorama.Fore.CYAN,
            "white": colorama.Fore.WHITE,
            "black": colorama.Fore.BLACK,
        }

        # Stores defined variables (e.g., {"myVar": "hello"})
        self.variables = {}
        # Stores lines of code when in 'compiler' mode, to be executed later
        self.program_lines = []
        # Current operating mode: "compiler" (default) or "interpreter"
        self.mode = "compiler"
        # Stores a history of all commands entered in the current session
        self.session_history = []
        # Stores the last input received from a 'show input' command
        self.last_input_value = None

    def _get_ansi_color_code(self, color_name_or_hex):
        """
        Returns the ANSI escape code for a given color name or hex code using Colorama.
        Hex code support is limited to basic terminal capabilities and will fall back.
        """
        color_name_or_hex_lower = color_name_or_hex.lower()
        if color_name_or_hex_lower in self.ANSI_COLORS:
            return self.ANSI_COLORS[color_name_or_hex_lower]
        elif re.match(r'^#([0-9a-f]{3}){1,2}$', color_name_or_hex_lower):
            # For hex codes (e.g., #FF00FF or #F00), standard ANSI terminals don't support direct hex.
            # We'll print a warning and return an empty string, meaning no color is applied.
            print(f"Warning: Hex color '{color_name_or_hex}' is not fully supported in this basic terminal environment. Displaying with default color.")
            return ""
        return "" # Return empty string if color not found or supported

    def _get_user_input(self, prompt=""):
        """
        Prompts the user for input and returns it.
        """
        return input(prompt)

    def _parse_and_execute_line(self, line, is_runtime_execution=False):
        """
        Parses and executes a single line of ZCLI code.
        This function now handles 'show input' and 'show ((input))' for both
        interpreter and compiled execution, ensuring input prompts appear only
        during execution.
        If is_runtime_execution is True, it means this is part of a program execution,
        and certain commands (like 'execute', 'save', 'open', 'int', 'comp') are ignored
        to prevent unexpected behavior or infinite loops.
        """
        # Add to session history only if it's a direct user input, not during program execution
        if not is_runtime_execution:
            self.session_history.append(line)

        # Ignore lines that are empty or start with the comment character '$'
        if not line.strip() or line.strip().startswith('$'):
            return

        # --- Color Tag Parsing ---
        color_code = ""
        # Regex to find ((color <color_name_or_hex>)) at the end of the line, allowing for optional spaces
        color_tag_pattern = r'\s*\(\(color\s+([a-zA-Z0-9#]+)\)\)\s*$'
        color_match = re.search(color_tag_pattern, line)

        if color_match:
            color_name_or_hex = color_match.group(1) # Extract the color argument (e.g., "red", "#FF00FF")
            color_code = self._get_ansi_color_code(color_name_or_hex)
            # Remove the color tag from the line before parsing the command
            processed_line = re.sub(color_tag_pattern, '', line).strip()
        else:
            processed_line = line.strip()

        # Split the processed line into parts: command, variable/target, and value (if any)
        parts = processed_line.split(maxsplit=2)

        if not parts: # Handle case where line becomes empty after removing color tag
            return

        command = parts[0].lower() # The first word is the command

        try: # Added try-except block for general command execution errors
            if command == "define":
                # Syntax: define <variable_name> "<value>" or define <variable_name> ((input)) or define <var> <part1> : <part2>
                if len(parts) >= 2: # At least "define varname"
                    var_name = parts[1]
                    if len(parts) < 3: # If no value part is provided
                        print("Error: Invalid define syntax. Missing value. Use: define variablename \"value\" or define variablename ((input)) or define <var> <part1> : <part2>")
                        return

                    # Get the full argument string for the value part
                    full_value_argument = processed_line[len("define") + len(var_name) + 1:].strip()

                    # Split by ':' to find concatenation parts
                    concatenation_parts = [p.strip() for p in re.split(r'\s*:\s*', full_value_argument)]

                    evaluated_value_parts = []
                    for part in concatenation_parts:
                        if not part: # Handle empty parts from splitting (e.g., "a::b")
                            continue

                        if part.startswith('"') and part.endswith('"'):
                            evaluated_value_parts.append(part[1:-1]) # Extract literal string
                        elif part.lower() == "((input))":
                            if self.last_input_value is not None:
                                evaluated_value_parts.append(self.last_input_value) # Use last input
                            else:
                                print("Error: No input has been provided yet via 'show input' for 'define ((input))'.")
                                return
                        elif part.startswith('(') and part.endswith(')'):
                            # Handle (variable_name) or ((variable_name))
                            var_name_in_paren = part[1:-1] # Remove outer parentheses
                            # If it's still wrapped in parentheses, remove inner ones too
                            if var_name_in_paren.startswith('(') and var_name_in_paren.endswith(')'):
                                var_name_in_paren = var_name_in_paren[1:-1]
                            
                            if var_name_in_paren in self.variables:
                                evaluated_value_parts.append(self.variables[var_name_in_paren]) # Get variable's value
                            else:
                                print(f"Error: Variable '{var_name_in_paren}' not defined in define concatenation.")
                                return
                        else:
                            print(f"Error: Invalid element '{part}' in define value concatenation. Must be a quoted string, ((input)), or (variable).")
                            return

                    value_to_store = "".join(evaluated_value_parts)
                    self.variables[var_name] = value_to_store
                    if not is_runtime_execution:
                        print(f"Defined variable '{var_name}' with value '{self.variables[var_name]}'")
                else:
                    print("Error: Invalid define syntax. Use: define variablename \"value\" or define variablename ((input)) or define <var> <part1> : <part2>")
            elif command == "show":
                # Syntax: show "<literal_string>" or show (<variable_name>) or show input ["<prompt_string>"] or show ((input))
                if len(parts) < 2:
                    print("Error: Invalid show syntax. Use: show \"literal string\", show (variablename), show input [\"prompt\"], show ((input)), or use concatenation with ':'")
                    return

                # Store the final content to show, which might be empty if only prompting
                content_to_print = ""
                
                # Check for 'show input' or 'show ((input))' as primary targets first
                # These should not be part of concatenation initially, but standalone 'show' commands.
                if parts[1].lower() == "input": # Handles 'show input ["prompt"]'
                    input_prompt = "" # Default prompt is empty
                    if len(parts) >= 3: # Check if a custom prompt is provided
                        prompt_part = parts[2]
                        if prompt_part.startswith('"') and prompt_part.endswith('"'):
                            input_prompt = prompt_part[1:-1] # Use custom quoted prompt
                        else:
                            print("Error: Invalid show input syntax. Prompt must be a quoted string.")
                            return
                    user_input_val = self._get_user_input(input_prompt) # Get input
                    self.last_input_value = user_input_val # Store the input
                    # Do NOT set content_to_print here, as we don't want to print it immediately
                    # The intent is to just prompt and store.
                elif parts[1].lower() == "((input))": # Handles 'show ((input))'
                    if self.last_input_value is not None:
                        content_to_print = self.last_input_value # Retrieve and print last input
                    else:
                        print("Error: No input has been provided yet via 'show input' for 'show ((input))'.")
                        return
                else:
                    # If it's not 'show input' or 'show ((input))', then proceed with concatenation parsing
                    # Get the full argument string after "show"
                    # This allows parsing of concatenated parts, excluding the "show" command itself
                    full_show_argument = processed_line[len("show"):].strip()

                    # Split by ':' to find concatenation parts
                    # Use re.split to handle spaces around ':'
                    concatenation_parts = [p.strip() for p in re.split(r'\s*:\s*', full_show_argument)]

                    final_output_content_parts = []
                    for part in concatenation_parts:
                        if not part: # Handle empty parts from splitting (e.g., "a::b")
                            continue

                        if part.startswith('"') and part.endswith('"'):
                            final_output_content_parts.append(part[1:-1]) # Extract literal string (without quotes)
                        elif part.startswith('(') and part.endswith(')'):
                            # Handle show (variable_name) or ((variable_name))
                            var_name_in_paren = part[1:-1] # Remove outer parentheses
                            # If it's still wrapped in parentheses, remove inner ones too
                            if var_name_in_paren.startswith('(') and var_name_in_paren.endswith(')'):
                                var_name_in_paren = var_name_in_paren[1:-1]
                            
                            if var_name_in_paren in self.variables:
                                final_output_content_parts.append(self.variables[var_name_in_paren]) # Get variable's value
                            else:
                                print(f"Error: Variable '{var_name_in_paren}' not defined in concatenation.")
                                return # Exit function if variable not found
                        # IMPORTANT: 'input' and '((input))' should NOT be directly handled here
                        # if they are part of a concatenation, as their primary forms are handled above.
                        # If they appear in concatenation, they would be treated as literal strings or error.
                        # For this scope, we assume 'input' and '((input))' are top-level show arguments.
                        else:
                            # If it's not a recognized type within concatenation, it's an error
                            print(f"Error: Invalid element '{part}' in show concatenation. Must be a quoted string or (variable).")
                            return

                    content_to_print = "".join(final_output_content_parts)

                # Only print if content_to_print is not empty (i.e., not a pure 'show input' command)
                if content_to_print or parts[1].lower() != "input": # Ensure we don't print for pure 'show input'
                    print(f"{color_code}{content_to_print}{self.ANSI_RESET}")
            elif command == "help":
                if not is_runtime_execution: # Help is a meta-command, not typically part of a program
                    self._print_help()
            elif command == "save":
                if not is_runtime_execution: # Save is a meta-command
                    if len(parts) >= 2:
                        filename = parts[1]
                        self._save_program(filename)
                    else:
                        print("Error: Invalid save syntax. Use: save filename")
            elif command == "open":
                if not is_runtime_execution: # Open is a meta-command
                    if len(parts) >= 2:
                        filename = parts[1]
                        self._open_program(filename)
                    else:
                        print("Error: Invalid open syntax. Use: open filename.zcli")
            elif command == "execute":
                if not is_runtime_execution: # Execute is a meta-command
                    if self.mode == "compiler":
                        if not self.program_lines:
                            print("No program lines to execute. Add commands in compiler mode first.")
                            return
                        print("\n--- Executing ZCLI Program ---")
                        # Temporarily switch to interpreter mode for execution
                        original_mode = self.mode
                        self.mode = "interpreter"
                        self._run_program_lines(self.program_lines) # This is where compiled lines are run
                        self.mode = original_mode # Restore original mode
                        print("--- Program Execution Complete ---\n")
                    else:
                        print("Error: 'execute' command is only available in compiler mode.")
                else:
                    # Ignore 'execute' if called from within a running program
                    print("Warning: 'execute' command ignored during program execution.")
            elif command == "int":
                if not is_runtime_execution:
                    self.mode = "interpreter"
                    print("Switched to interpreter mode. Commands will be executed immediately.")
                else:
                    print("Warning: 'int' command ignored during program execution.")
            elif command == "comp":
                if not is_runtime_execution:
                    self.mode = "compiler"
                    print("Switched to compiler mode. Commands will be stored for 'execute'.")
                else:
                    print("Warning: 'comp' command ignored during program execution.")
            else:
                # If the command is not recognized
                if not is_runtime_execution: # Only show error if direct user input
                    print(f"Error: Unknown command '{command}'. Type 'help' for commands.")
        except Exception as e:
            print(f"Runtime Error during command '{command}': {e}")
            # If it's a runtime error during compiled execution, we should probably stop.
            if is_runtime_execution:
                print("Program execution halted due to the above error.")
                sys.exit(1) # Exit with an error code

    def _run_program_lines(self, lines):
        """
        Executes a list of ZCLI program lines, typically used by the 'execute' command
        or when opening a file in interpreter mode.
        """
        for line in lines:
            try: # Added try-except for individual line execution
                # Execute each line, signaling that it's part of a runtime execution
                self._parse_and_execute_line(line, is_runtime_execution=True)
            except SystemExit: # Catch SystemExit if _parse_and_execute_line decided to exit
                raise # Re-raise to stop the program
            except Exception as e:
                print(f"Error executing line '{line}': {e}")
                print("Program execution halted.")
                sys.exit(1) # Exit on first error during program execution

    def _print_help(self):
        """Prints the available ZCLI commands and their syntax."""
        print("\n----------------------------------------------------------------")
        print("                 Welcome to ZCLI! Help Guide")
        print("----------------------------------------------------------------")
        print("Commands:")
        print("  define <variable_name> \"<value>\"")
        print("    - Defines a new variable with a literal string value.")
        print("    Example: define myVar \"Hello ZCLI!\"")
        print("")
        print("  define <variable_name> ((input))")
        print("    - Defines a new variable with the last input received from a 'show input' command.")
        print("    - Does NOT prompt for new input.")
        print("    Example: define userName ((input))")
        print("")
        print("  define <variable_name> <part1> : <part2> : ...")
        print("    - Defines a new variable by concatenating multiple parts.")
        print("    - Parts can be literal strings, ((input)), or (variable_name).")
        print("    Example: define fullName (firstName) : \" \" : (lastName)")
        print("")
        print("  show \"<literal_string>\" or show (<variable_name>)")
        print("    - Prints a literal string or the value of a variable.")
        print("    - Supports concatenation with ':' (e.g., show \"Hello\" : (myVar) : \"!\")")
        print("    - Supports optional color tag at the end: ((color <color_name_or_hex>))")
        print("    Example: show \"This is a literal string.\" ((color red))")
        print("    Example: show (myVar) ((color blue))")
        print("    Example: show \"Your name is: \" : (userName)")
        print("")
        print("  show input [\"<prompt_string>\"]")
        print("    - Prompts for user input with an optional custom message.")
        print("    - The input received is stored for 'define ((input))' and 'show ((input))'.")
        print("    - Does NOT print the input directly after prompting.")
        print("    Example: show input (prompts for input with no message)")
        print("    Example: show input \"What is your name? \" (prompts with custom message)")
        print("")
        print("  show ((input))")
        print("    - Prints the last input received from a 'show input' command.")
        print("    - Does NOT prompt for new input.")
        print("    Example: show ((input))")
        print("    Supported named colors: red, orange, yellow, green, blue, indigo, violet, purple, cyan, white, black.")
        print("    Note: Hex color codes (e.g., #FF00FF) are recognized but may not display correctly in all terminals.")
        print("")
        print("  $ <comment_text>")
        print("    - Adds a comment. Lines starting with '$' are ignored.")
        print("    Example: $ This is a comment about my code.")
        print("")
        print("  save <filename>")
        print("    - Saves the current program (if in compiler mode) or session history")
        print("      (if in interpreter mode) to the specified file. Automatically adds '.zcli' extension.")
        print("    Example: save myprogram (will save as myprogram.zcli)")
        print("")
        print("  open <filename.zcli>")
        print("    - Loads commands from the specified file.")
        print("    - In compiler mode: Appends lines to the current program buffer.")
        print("    - In interpreter mode: Executes lines immediately.")
        print("    Example: open myprogram.zcli")
        print("")
        print("  execute")
        print("    - (Compiler Mode Only) Executes all stored program lines.")
        print("    Example: execute")
        print("")
        print("  int")
        print("    - Switches ZCLI to interpreter mode. Commands execute immediately.")
        print("    Example: int")
        print("")
        print("  comp")
        print("    - Switches ZCLI to compiler mode. Commands are stored for 'execute'.")
        print("    Example: comp")
        print("")
        print("  exit")
        print("    - Exits the ZCLI environment.")
        print("----------------------------------------------------------------\n")

    def _save_program(self, filename):
        """
        Saves the current program lines (if in compiler mode) or the session history
        (if in interpreter mode) to the specified file.
        Automatically appends '.zcli' extension if not present.
        """
        if not filename.lower().endswith(".zcli"):
            filename += ".zcli"
        try:
            with open(filename, 'w') as f:
                if self.mode == "compiler":
                    # Save the program lines that have been buffered
                    for line in self.program_lines:
                        f.write(line + '\n')
                    print(f"Program (compiler buffer) saved to '{filename}'.")
                else:
                    # Save the entire session history
                    for line in self.session_history:
                        f.write(line + '\n')
                    print(f"Session history saved to '{filename}'.")
        except IOError as e:
            print(f"Error saving file '{filename}': {e}")

    def _open_program(self, filename):
        """
        Opens a ZCLI program file.
        If in compiler mode, it loads the lines into the program buffer.
        If in interpreter mode, it executes them immediately.
        """
        try:
            with open(filename, 'r') as f:
                # Read all non-empty lines from the file
                lines = [line.strip() for line in f if line.strip()]
                if self.mode == "compiler":
                    self.program_lines.extend(lines) # Add to current program buffer
                    print(f"Program lines from '{filename}' loaded into compiler buffer.")
                    print("Type 'execute' to run them.")
                else:
                    print(f"Executing program from '{filename}' in interpreter mode...")
                    self._run_program_lines(lines) # Execute immediately
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except IOError as e:
            print(f"Error opening file '{filename}': {e}")

    def run_repl(self, file_to_execute=None): # Added file_to_execute parameter
        """
        Runs the main ZCLI Read-Eval-Print Loop (REPL).
        If file_to_execute is provided, it runs that file and exits.
        Otherwise, it starts the interactive REPL.
        """
        if file_to_execute:
            if not os.path.exists(file_to_execute):
                print(f"Error: File '{file_to_execute}' not found.")
                sys.exit(1) # Exit if file doesn't exist

            print(f"Executing ZCLI file: {file_to_execute}")
            # Ensure we are in interpreter mode for direct file execution
            original_mode = self.mode
            self.mode = "interpreter"
            try:
                self._open_program(file_to_execute) # This will execute the lines
            except SystemExit: # Catch SystemExit from _run_program_lines if an error occurred
                pass # Already printed error, just exit gracefully
            finally:
                self.mode = original_mode # Restore original mode
            print(f"Finished executing {file_to_execute}.")
            return # Exit after executing the file

        print("Welcome to ZCLI! Type 'help' for commands.")
        while True:
            try:
                # Display a different prompt based on the current mode
                prompt_char = ">>" if self.mode == "interpreter" else ">" # Changed prompts
                user_input = input(f"ZCLI {prompt_char} ")

                if user_input.lower() == "exit":
                    print("Exiting ZCLI. Goodbye!")
                    break

                # If in compiler mode, store the command for later execution,
                # unless it's a control command that should run immediately.
                if self.mode == "compiler":
                    # Control commands that execute immediately even in compiler mode
                    control_commands = ["execute", "help", "save", "open", "int", "comp", "exit"]
                    
                    # Check if the input is a control command (ignoring color tag for this check)
                    # This regex removes the color tag for the command check, but keeps the original for storage
                    temp_line_for_command_check = re.sub(r'\s*\(\(color\s+([a-zA-Z0-9#]+)\)\)\s*$', '', user_input).strip()

                    if any(temp_line_for_command_check.lower().startswith(cmd) for cmd in control_commands):
                        # If it's a control command, execute it immediately.
                        self._parse_and_execute_line(user_input)
                    else:
                        # Otherwise (for define, show, comments), add it to program lines.
                        self.program_lines.append(user_input)
                        
                else: # Interpreter mode
                    # In interpreter mode, all commands are parsed and executed immediately
                    self._parse_and_execute_line(user_input)
            except EOFError: # Handles Ctrl+D for exiting
                print("\nExiting ZCLI. Goodbye!")
                break
            except Exception as e:
                # Catch any unexpected errors during input or processing
                print(f"An unexpected error occurred: {e}")

# Main execution block: This runs when the script is executed
if __name__ == "__main__":
    zcli = ZCLILanguage() # Create an instance of our ZCLI language
    
    # Check if a file path is provided as a command-line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        zcli.run_repl(file_path) # Run the file directly
    else:
        zcli.run_repl() # Start the interactive REPL
