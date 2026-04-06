import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
dotenv.config();

const genai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const PROMPT_TEMPLATE = `
Analyze this medical report and return strictly in JSON. You are an expert medical AI.

JSON FORMAT:
{
  "patient_summary": "Detailed summary of the patient's general health based on report.",
  "abnormal_values": [
    { "name": "Marker Name", "value": "Value", "normal_range": "Range", "status": "Low/High/Optimal" }
  ],
  "key_findings": ["Finding 1", "Finding 2"],
  "risk_level": "Low | Medium | High",
  "recommendations": ["Recommendation 1"]
}

Only return valid JSON. No extra text. Do not wrap in markdown quotes if possible, just RAW JSON format starting with { and ending with }.

MEDICAL REPORT DATA:
`;

/**
 * Send a chunk or combined text to Gemini with fallback mechanism
 */
export const analyzeWithGemini = async (text, isFinalMerge = false) => {
    let responseText = "";

    const prompt = isFinalMerge 
        ? `Merge these partial medical report analyses into ONE final cohesive summary following this exact JSON format. Deduplicate abnormal values and findings.\n\n${PROMPT_TEMPLATE}\n\nDATA TO MERGE:\n${text}`
        : `${PROMPT_TEMPLATE}\n${text}`;

    try {
        // Try Pro model first
        const response = await genai.models.generateContent({
            model: 'gemini-2.5-pro',
            contents: prompt,
            config: {
                temperature: 0.1,
            }
        });
        responseText = response.text;
    } catch (proError) {
        console.warn('Pro model failed, trying Flash model...', proError.message);
        try {
            // Fallback to Flash
            const response = await genai.models.generateContent({
                model: 'gemini-2.5-flash',
                contents: prompt,
                config: {
                    temperature: 0.1,
                }
            });
            responseText = response.text;
        } catch (flashError) {
            console.error('All Gemini models failed:', flashError.message);
            throw new Error('Gemini API Integration Failure');
        }
    }

    return responseText;
};

/**
 * Parse the raw string response from Gemini into a valid JS Object
 */
export const parseJSONResponse = (raw) => {
    try {
        let cleanText = raw.trim();
        // Remove markdown block backticks if present
        if (cleanText.startsWith('\`\`\`json')) {
            cleanText = cleanText.substring(7);
        }
        if (cleanText.startsWith('\`\`\`')) {
            cleanText = cleanText.substring(3);
        }
        if (cleanText.endsWith('\`\`\`')) {
            cleanText = cleanText.substring(0, cleanText.length - 3);
        }
        
        return JSON.parse(cleanText.trim());
    } catch (err) {
        console.error('Failed to parse Gemini output to JSON:', raw.substring(0, 50));
        throw new Error('Invalid JSON format returned from Gemini');
    }
};
