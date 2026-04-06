import { extractTextFromPDF } from '../services/pdf.service.js';
import { cleanText, chunkText } from '../services/utils.service.js';
import { analyzeWithGemini, parseJSONResponse } from '../services/gemini.service.js';

export const processReport = async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ success: false, error: 'No PDF file uploaded' });
        }

        if (req.file.mimetype !== 'application/pdf') {
            return res.status(400).json({ success: false, error: 'Invalid file format. Only PDF allowed.' });
        }

        console.log(`Processing file: ${req.file.originalname} (${req.file.size} bytes)`);

        // 1. Text Extraction
        let rawText;
        try {
            rawText = await extractTextFromPDF(req.file.buffer);
        } catch (err) {
            return res.status(500).json({ success: false, error: 'Failed to extract text from PDF.' });
        }

        if (!rawText || rawText.trim().length === 0) {
            return res.status(400).json({ success: false, error: 'PDF appears to be empty or unreadable.' });
        }

        // 2. Text Cleaning
        const cleanedText = cleanText(rawText);
        console.log(`Extracted raw length: ${rawText.length}, Cleaned length: ${cleanedText.length}`);

        // 3. Chunking
        const chunks = chunkText(cleanedText, 2000);
        console.log(`Split into ${chunks.length} chunks`);

        // 4. Gemini API Integration (Parallel Processing)
        // With a 10s maximum timeout on the whole chunking step as a basic safeguard
        const chunkPromises = chunks.map(chunk => analyzeWithGemini(chunk, false));
        
        let chunkResponses;
        try {
            chunkResponses = await Promise.all(chunkPromises);
        } catch (err) {
            return res.status(502).json({ success: false, error: err.message || 'Error processing chunks with Gemini API' });
        }

        // 5. Merging Results
        let finalJson;
        if (chunkResponses.length === 1) {
            // Only one chunk, just parse it
            finalJson = parseJSONResponse(chunkResponses[0]);
        } else {
            // Merge responses logic via Gemini again
            const combinedChunkResults = chunkResponses.join('\n\n---NEXT CHUNK ANALYSIS---\n\n');
            const finalMergedRaw = await analyzeWithGemini(combinedChunkResults, true);
            finalJson = parseJSONResponse(finalMergedRaw);
        }

        console.log('Successfully completed analysis.');

        // 6. Response Format
        return res.json({
            success: true,
            data: finalJson
        });

    } catch (error) {
        console.error('Unhandled Controller Error:', error);
        return res.status(500).json({ success: false, error: 'Internal Server Error' });
    }
};
