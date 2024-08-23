import ast


def string_to_dict(input_string):
    # Using ast.literal_eval for safe evaluation of the string
    try:
        result = ast.literal_eval(input_string)
        return result
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing string to dictionary: {e}")
        return None
