import os
import json
import re

def parse_xcookybooky_recipe(content):
    """
    Parse a single xcookybooky recipe from LaTeX content.
    Returns a dict with Mealie-compatible fields.
    """
    recipe = {
        "name": "",
        "description": "",
        "image": None,
        "recipeYield": "",
        "recipeIngredient": [],
        "recipeInstructions": [],
        "totalTime": "",
        "prepTime": "",
        "cookTime": "",
        "performTime": None,
        "recipeCategory": [],
        "tags": [],
        "rating": 0,
        "orgURL": None,
        "extras": {},
        "notes": [],
        "nutrition": {},
        "assets": [],
        "dateAdded": None,
        "dateUpdated": None
    }

    # Extract recipe: \begin{recipe}[options]{title}
    start = content.find('\\begin{recipe}[')
    if start != -1:
        options_start = start + len('\\begin{recipe}[')
        options_end = content.find(']', options_start)
        if options_end != -1:
            options = content[options_start:options_end]
            title_start = options_end + 1
            if title_start < len(content) and content[title_start] == '{':
                title_end = content.find('}', title_start)
                print(f"title_start: {title_start}, title_end: {title_end}")  # Debug
                print(f"content[title_start:title_end+1]: {repr(content[title_start:title_end+1])}")  # Debug
                if title_end != -1:
                    recipe["name"] = content[title_start+1:title_end].strip()
                else:
                    recipe["name"] = ""
            else:
                recipe["name"] = ""
        else:
            options = ""
            recipe["name"] = ""
    else:
        options = ""
        recipe["name"] = ""

    print(f"Options: {repr(options)}")  # Debug
    print(f"Name: {repr(recipe['name'])}")  # Debug
    prep_time_match = re.search(r'preparationtime\s*=\s*\{\\unit\[(\d+)\]\{Min\}\}', options)
    if prep_time_match:
        prep_time = prep_time_match.group(1)
        recipe["prepTime"] = f"PT{prep_time}M"

    baking_time_match = re.search(r'bakingtime\s*=\s*\{\\unit\[(\d+)\]\{Min\}\}', options)
    if baking_time_match:
        baking_time = baking_time_match.group(1)
        recipe["cookTime"] = f"PT{baking_time}M"
        if prep_time_match:
            total = int(prep_time) + int(baking_time)
            recipe["totalTime"] = f"PT{total}M"

    portion_match = re.search(r'portion\s*=\s*([^,}]+)', options)
    if portion_match:
        recipe["recipeYield"] = portion_match.group(1).strip()

    baking_temp_match = re.search(r'bakingtemperature\s*=\s*\{\\protect\\bakingtemperature\{([^=]+)=\s*\\unit\[(\d+)\]\{\\textcelsius\}\}\}', options)
    if baking_temp_match:
        method = baking_temp_match.group(1)
        temp = baking_temp_match.group(2)
        recipe["extras"]["bakingMethod"] = method
        recipe["extras"]["bakingTemperature"] = f"{temp}°C"

        # Parse options
        prep_time_match = re.search(r'preparationtime\s*=\s*\{\\unit\[(\d+)\]\{Min\}\}', options)
        if prep_time_match:
            prep_time = prep_time_match.group(1)
            recipe["prepTime"] = f"PT{prep_time}M"

        baking_time_match = re.search(r'bakingtime\s*=\s*\{\\unit\[(\d+)\]\{Min\}\}', options)
        if baking_time_match:
            baking_time = baking_time_match.group(1)
            recipe["cookTime"] = f"PT{baking_time}M"
            if prep_time_match:
                total = int(prep_time) + int(baking_time)
                recipe["totalTime"] = f"PT{total}M"

        portion_match = re.search(r'portion\s*=\s*([^,}]+)', options)
        if portion_match:
            recipe["recipeYield"] = portion_match.group(1).strip()

        baking_temp_match = re.search(r'bakingtemperature\s*=\s*\{\\protect\\bakingtemperature\{([^=]+)=\s*\\unit\[(\d+)\]\{\\textcelsius\}\}\}', options)
        if baking_temp_match:
            method = baking_temp_match.group(1)
            temp = baking_temp_match.group(2)
            recipe["extras"]["bakingMethod"] = method
            recipe["extras"]["bakingTemperature"] = f"{temp}°C"

    # Extract source: \source{...}
    source_match = re.search(r'\\source\s*\{([^}]*)\}', content)
    if source_match:
        recipe["orgURL"] = source_match.group(1).strip()

    # Extract ingredients: \ingredients{ ... }
    ingredients_match = re.search(r'\\ingredients\s*\{(.*?)\}', content, re.DOTALL)
    if ingredients_match:
        ingredients_text = ingredients_match.group(1)
        lines = ingredients_text.split('\\\\')
        for line in lines:
            line = line.strip()
            if '&' in line and not line.startswith('\\multicolumn'):
                parts = line.split('&')
                if len(parts) > 1:
                    ingredient = parts[1].strip()
                    # Remove LaTeX commands like \index{...}
                    ingredient = re.sub(r'\\index\{[^}]*\}', '', ingredient)
                    ingredient = re.sub(r'\\unit\[([^\]]*)\]\{([^\}]*)\}', r'\1 \2', ingredient)
                    if ingredient:
                        recipe["recipeIngredient"].append(ingredient)

    # Extract preparation: \preparation{ ... \step ... }
    preparation_match = re.search(r'\\preparation\s*\{(.*?)\}', content, re.DOTALL)
    if preparation_match:
        prep_text = preparation_match.group(1)
        steps = re.findall(r'\\step\s*(.*?)(?=\\step|$)', prep_text, re.DOTALL)
        recipe["recipeInstructions"] = [{"text": step.strip()} for step in steps if step.strip()]

    # Extract hint as notes
    hint_match = re.search(r'\\hint\s*\{(.*?)\}', content, re.DOTALL)
    if hint_match:
        recipe["notes"].append({"title": "Hint", "text": hint_match.group(1).strip()})

    # Extract calories as nutrition
    calories_match = re.search(r'\\calories\s*\{([^}]*)\}', content)
    if calories_match:
        recipe["nutrition"]["calories"] = calories_match.group(1).strip()

    return recipe

def convert_tex_to_json(tex_file_path, output_dir):
    """
    Convert a .tex file containing xcookybooky recipes to JSON files.
    Assumes each \begin{recipe} starts a new recipe.
    """
    with open(tex_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content by \begin{recipe} commands
    recipes = re.split(r'\\begin\{recipe\}', content)[1:]  # Skip before first recipe

    for i, recipe_content in enumerate(recipes):
        # Find the end of the recipe
        end_match = re.search(r'\\end\{recipe\}', recipe_content)
        if end_match:
            recipe_content = recipe_content[:end_match.start()]
        recipe_data = parse_xcookybooky_recipe('\\begin{recipe}' + recipe_content)
        if recipe_data["name"]:
            json_file = os.path.join(output_dir, f"{recipe_data['name'].replace(' ', '_')}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(recipe_data, f, indent=2, ensure_ascii=False)
            print(f"Created {json_file}")

def main():
    # Example usage: convert all .tex files in current directory to JSON in 'output' dir
    input_dir = '.'  # Change to your tex files directory
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)

    for file in os.listdir(input_dir):
        if file.endswith('.tex'):
            convert_tex_to_json(os.path.join(input_dir, file), output_dir)

if __name__ == "__main__":
    main()