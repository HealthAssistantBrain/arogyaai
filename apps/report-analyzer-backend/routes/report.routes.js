import express from 'express';
import multer from 'multer';
import { processReport } from '../controllers/report.controller.js';

const router = express.Router();
// Use memory storage for security -> do not store permanent PDFs
const upload = multer({ storage: multer.memoryStorage() });

router.post('/analyze-report', upload.single('report'), processReport);

export default router;
