#!/bin/bash

# Set layout type for README.md files (project index)
LAYOUT_TYPE="page"

# Set layout type for documentation files in the docs folder
DOCS_LAYOUT_TYPE="page"

# Force submodule update (set to true to force changes)
FORCE_SUBMODULE_UPDATE=true

# If FORCE_SUBMODULE_UPDATE is true, reinitialize and update submodules
if [ "$FORCE_SUBMODULE_UPDATE" = true ]; then
    echo "Forcing submodule update..."
    git submodule update --init --recursive --force
else
    echo "Normal submodule update..."
    git submodule update --remote --merge
fi

# Loop through each project in the _projects folder
for project in _projects/*; do
    if [ -d "$project/docs" ]; then
        # Copy assets folder (if it exists)
        if [ -d "$project/assets" ]; then
            cp -r "$project/assets"/* assets/
        fi
        
        # Check if README.md exists and create it as the project index
        if [ -f "$project/README.md" ]; then
            readme_file="$project/README.md"
            readme_title=$(basename "$project" | sed -e 's/-/ /g' -e 's/\b\(.\)/\u\1/g')
            
            # Check if front matter exists in the README
            if ! grep -q "^---" "$readme_file"; then
                # Add front matter with the proper permalink, title, and layout type
                echo -e "---\nlayout: $LAYOUT_TYPE\ntitle: \"$readme_title\"\npermalink: /projects/$(basename "$project")/\n---\n$(cat "$readme_file")" > "$readme_file"
            fi
        fi
        
        # Process each markdown file in docs
        find "$project/docs" -name "*.md" | while read -r file; do
            # Extract relative path from the docs folder and generate a URL-friendly title
            relative_path=${file#"$project/docs/"}
            filename=$(basename "$relative_path" .md)
            title=$(echo "$filename" | sed -e 's/-/ /g' -e 's/\b\(.\)/\u\1/g')
            
            # Check if front matter exists
            if ! grep -q "^---" "$file"; then
                # Add front matter with a proper permalink, title, and docs layout type
                echo -e "---\nlayout: $DOCS_LAYOUT_TYPE\ntitle: \"$title\"\npermalink: /projects/$(basename "$project")/docs/${relative_path%.md}/\n---\n$(cat "$file")" > "$file"
            fi
        done
    fi
done

echo "Documentation and assets synced, front matter added."
