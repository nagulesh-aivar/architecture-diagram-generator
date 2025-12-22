#!/bin/bash
# Cleanup script to consolidate all diagrams to a single location

cd /Users/dhanavarshini/Hackathon/h1/architecture-diagram-generator/Backend

echo "🧹 Cleaning up and consolidating diagram storage..."
echo ""

# Create the single output directory
mkdir -p outputs/generated-diagrams

echo "📂 Moving diagrams from /Backend/ root to outputs/generated-diagrams/..."
# Move any PNG files from Backend root (except valid diagrams with timestamps)
for file in *.png; do
    if [ -f "$file" ]; then
        # Check if it's a timestamped diagram (format: YYYYMMDD_HHMMSS_UUID_diagram.png)
        if [[ "$file" =~ ^[0-9]{8}_[0-9]{6}_.+_diagram\.png$ ]]; then
            echo "  Moving: $file"
            mv "$file" outputs/generated-diagrams/
        else
            echo "  Removing old/test diagram: $file"
            rm "$file"
        fi
    fi
done

echo ""
echo "📂 Moving diagrams from generated-diagrams/ to outputs/generated-diagrams/..."
# Move diagrams from the duplicate generated-diagrams folder
if [ -d "generated-diagrams" ]; then
    for file in generated-diagrams/*.png; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            # Check if it's a valid diagram
            if [[ "$filename" =~ ^[0-9]{8}_[0-9]{6}_.+_diagram\.png$ ]]; then
                # Check if file already exists in destination
                if [ ! -f "outputs/generated-diagrams/$filename" ]; then
                    echo "  Moving: $filename"
                    mv "$file" outputs/generated-diagrams/
                else
                    echo "  Skipping duplicate: $filename"
                    rm "$file"
                fi
            else
                echo "  Removing invalid/test file: $filename"
                rm "$file"
            fi
        fi
    done
    
    # Remove the duplicate folder if empty
    if [ -z "$(ls -A generated-diagrams)" ]; then
        echo "  Removing empty generated-diagrams/ folder"
        rmdir generated-diagrams
    fi
fi

echo ""
echo "📂 Checking outputs/generated-diagrams/ for nested folders..."
# Remove any nested generated-diagrams folders
if [ -d "outputs/generated-diagrams/generated-diagrams" ]; then
    echo "  Found nested folder, moving contents up..."
    mv outputs/generated-diagrams/generated-diagrams/* outputs/generated-diagrams/ 2>/dev/null || true
    rmdir outputs/generated-diagrams/generated-diagrams
fi

echo ""
echo "🧹 Removing duplicate diagrams in outputs/generated-diagrams/..."
# Remove files with .png.png extension (double extension)
for file in outputs/generated-diagrams/*.png.png; do
    if [ -f "$file" ]; then
        echo "  Removing: $(basename "$file")"
        rm "$file"
    fi
done

# Remove _moved files (duplicates)
for file in outputs/generated-diagrams/*_moved.png; do
    if [ -f "$file" ]; then
        echo "  Removing: $(basename "$file")"
        rm "$file"
    fi
done

echo ""
echo "📊 Final structure:"
echo "  Total diagrams: $(ls -1 outputs/generated-diagrams/*.png 2>/dev/null | wc -l | tr -d ' ')"
echo "  Location: outputs/generated-diagrams/"
echo ""

echo "✅ Cleanup complete!"
echo ""
echo "📁 All diagrams are now stored in:"
echo "   /Backend/outputs/generated-diagrams/"
echo ""
echo "🗑️  Removed:"
echo "   - Duplicate folders"
echo "   - Test/invalid diagrams"
echo "   - Files with .png.png extension"
echo "   - Moved/backup files"

