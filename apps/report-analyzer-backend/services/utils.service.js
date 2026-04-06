/**
 * Clean the extracted text by removing extra spaces, dots, and normalizing some patterns.
 */
export const cleanText = (text) => {
    if (!text) return '';
    return text
        // Remove repeated dots
        .replace(/\.{2,}/g, ' ')
        // Remove extra spaces and tabs
        .replace(/[ \t]+/g, ' ')
        // Normalize new line combinations
        .replace(/\n\s*\n/g, '\n')
        // Often PDFs have bad spacing in units like 'mg / dL', fix them
        .replace(/mg\s*\/\s*dL/gi, 'mg/dL')
        .replace(/g\s*\/\s*dL/gi, 'g/dL')
        .replace(/u\s*\/\s*L/gi, 'U/L')
        .trim();
};

/**
 * Split text into chunks of maximum `maxChars` length, ensuring we don't break at mid-word.
 */
export const chunkText = (text, maxChars = 2000) => {
    if (!text) return [];
    
    const chunks = [];
    let currentIndex = 0;
    
    while (currentIndex < text.length) {
        let endIndex = currentIndex + maxChars;
        
        if (endIndex >= text.length) {
            chunks.push(text.slice(currentIndex));
            break;
        }
        
        // Try to find the last space before the limit
        let lastSpaceIndex = text.lastIndexOf(' ', endIndex);
        let lastNewlineIndex = text.lastIndexOf('\n', endIndex);
        
        // Prefer breaking at newline, else space
        let breakIndex = Math.max(lastSpaceIndex, lastNewlineIndex);
        
        // If no safe break point was found, force break
        if (breakIndex <= currentIndex) {
            breakIndex = endIndex;
        }
        
        chunks.push(text.slice(currentIndex, breakIndex).trim());
        currentIndex = breakIndex;
    }
    
    return chunks;
};
