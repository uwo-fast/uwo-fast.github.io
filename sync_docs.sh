#!/bin/bash

# Ensure the submodules are updated
git submodule update --remote --merge

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
                # Add front matter with a proper permalink and title
                echo -e "---\nlayout: project-index\ntitle: \"$readme_title\"\npermalink: /projects/$(basename "$project")/\n---\n$(cat "$readme_file")" > "$readme_file"
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
                # Add front matter with a proper permalink and title
                echo -e "---\nlayout: project-docs\ntitle: \"$title\"\npermalink: /projects/$(basename "$project")/docs/${relative_path%.md}/\n---\n$(cat "$file")" > "$file"
            fi
        done
    fi
done

echo "Documentation and assets synced, front matter added."
