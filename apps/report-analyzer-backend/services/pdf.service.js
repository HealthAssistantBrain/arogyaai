import pdfParse from 'pdf-parse';

export const extractTextFromPDF = async (buffer) => {
    try {
        const data = await pdfParse(buffer);
        return data.text || '';
    } catch (error) {
        console.error('PDF parsing error:', error);
        throw new Error('Failed to extract text from PDF');
    }
};
