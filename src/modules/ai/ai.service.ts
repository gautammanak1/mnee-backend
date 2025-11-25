import { Injectable } from '@nestjs/common';
import { GoogleGenerativeAI } from '@google/generative-ai';
import axios from 'axios';

// import { InferenceClient } from '@huggingface/inference';

@Injectable()
export class AIService {
  private model: any;
  private geminiApiKey: string;

  // private client: InferenceClient; // HuggingFace client - commented out
  constructor() {
    if (!process.env.GEMINI_API_KEY) {
      throw new Error('GEMINI_API_KEY environment variable is not set');
    }
    // if (!process.env.HF_API_TOKEN) {
    //   throw new Error('HF_API_TOKEN environment variable is not set');
    // }
    // this.client = new InferenceClient(process.env.HF_API_TOKEN); // HuggingFace - commented out
    this.geminiApiKey = process.env.GEMINI_API_KEY;
    const genAI = new GoogleGenerativeAI(this.geminiApiKey);
    this.model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash-exp' });
    // For image generation, we'll use Google's Imagen API
  }

  /**
   * Generate a LinkedIn post based on a topic
   */
  async generateLinkedInPost(topic: string, includeHashtags: boolean = true, language: string = 'en'): Promise<{
    text: string;
    hashtags: string[];
  }> {
    const languageMap: { [key: string]: string } = {
      'en': 'English',
      'fr': 'French',
      'es': 'Spanish',
      'it': 'Italian',
      'de': 'German',
      'pt': 'Portuguese',
      'nl': 'Dutch',
    };
    
    const languageName = languageMap[language] || 'English';
    
    // Log for debugging
    console.log(`[AI Service] Generating post in language: ${language} (${languageName})`);
    
    // Language-specific instructions
    const languageInstructions: { [key: string]: string } = {
      'en': 'Write in English only. Use English words, grammar, and expressions.',
      'fr': 'Écrivez uniquement en français. Utilisez des mots, une grammaire et des expressions françaises.',
      'es': 'Escribe solo en español. Usa palabras, gramática y expresiones españolas.',
      'it': 'Scrivi solo in italiano. Usa parole, grammatica ed espressioni italiane.',
      'de': 'Schreibe nur auf Deutsch. Verwende deutsche Wörter, Grammatik und Ausdrücke.',
      'pt': 'Escreva apenas em português. Use palavras, gramática e expressões portuguesas.',
      'nl': 'Schrijf alleen in het Nederlands. Gebruik Nederlandse woorden, grammatica en uitdrukkingen.',
    };
    
    const langInstruction = languageInstructions[language] || languageInstructions['en'];
    
    const prompt = `You are a professional LinkedIn content writer. Generate a LinkedIn post about "${topic}".

🚨 CRITICAL LANGUAGE REQUIREMENT - THIS IS MANDATORY 🚨
${langInstruction}
The ENTIRE post must be written in ${languageName} ONLY. 
- Do NOT use English or any other language
- Every single word, sentence, and paragraph must be in ${languageName}
- If you write even one word in English, the response is WRONG
- The post content, hashtags, and all text must be in ${languageName}
- This is not optional - it is a strict requirement

Content Requirements:
- The post should be engaging, professional, and valuable to LinkedIn audience
- Length should be between 150-300 words
- Include a hook in the first line to grab attention
- Add value with insights, tips, or thought-provoking questions
- End with a call-to-action or question to encourage engagement
- Make it sound natural and authentic, not robotic
- Use professional but conversational tone
- Write EXCLUSIVELY in ${languageName} - no English, no code-switching, no mixing languages

${includeHashtags ? `Also suggest 3-5 relevant hashtags in ${languageName} for this post. Hashtags should be relevant to ${languageName}-speaking LinkedIn audience.` : ''}

VERIFICATION CHECKLIST BEFORE RESPONDING:
✓ Is every word in ${languageName}?
✓ Is there any English text? (If yes, rewrite it)
✓ Are hashtags in ${languageName}?
✓ Does the post sound natural in ${languageName}?

IMPORTANT: Your response must be a valid JSON object. The "text" field must contain the post written entirely in ${languageName}.

Format your response as JSON:
{
  "text": "the post content here written COMPLETELY in ${languageName} - no English allowed",
  "hashtags": ["#hashtag1", "#hashtag2", ...]
}`;

    try {
      const result = await this.model.generateContent(prompt);
      const response = result.response.text();
      
      // Try to parse JSON from response
      let parsed;
      try {
        // Extract JSON from markdown code blocks if present
        const jsonMatch = response.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          parsed = JSON.parse(jsonMatch[0]);
        } else {
          parsed = JSON.parse(response);
        }
      } catch (e) {
        // If JSON parsing fails, create a structured response from text
        const hashtags = includeHashtags 
          ? response.match(/#\w+/g) || []
          : [];
        const text = response.replace(/\{[\s\S]*\}/g, '').trim();
        parsed = {
          text: text || response,
          hashtags: hashtags.slice(0, 5),
        };
      }

      const generatedText = parsed.text || response;
      const generatedHashtags = parsed.hashtags || [];
      
      // Log the generated content for debugging
      console.log(`[AI Service] Generated post preview (first 100 chars): ${generatedText.substring(0, 100)}...`);
      console.log(`[AI Service] Language requested: ${languageName}, Hashtags: ${generatedHashtags.length}`);
      
      return {
        text: generatedText,
        hashtags: generatedHashtags,
      };
    } catch (error) {
      console.error('Error generating LinkedIn post:', error);
      console.error(`[AI Service] Error details - Language: ${language}, Topic: ${topic}`);
      throw new Error(`Failed to generate LinkedIn post: ${error.message}`);
    }
  }

  /**
   * Generate an image description/prompt for the topic
   */
  async generateImagePrompt(topic: string): Promise<string> {
    const prompt = `Create a detailed, professional image description for a LinkedIn post about "${topic}". 

The image should be:
- Professional and suitable for LinkedIn
- Visually appealing and relevant to the topic
- Clean, modern design style
- Appropriate for business/professional context

Return only the image description (no JSON, no markdown), suitable for an AI image generator.`;

    try {
      const result = await this.model.generateContent(prompt);
      return result.response.text().trim();
    } catch (error) {
      console.error('Error generating image prompt:', error);
      // Fallback to a simple description
      return `Professional illustration related to ${topic}, modern business style, clean design`;
    }
  }

  /**
   * Generate an image using Google's Imagen API via Gemini API
   * Uses Gemini API key directly - no Google Cloud setup required
   */
  async generateImage(prompt: string): Promise<Buffer> {
    try {
      // Using Generative AI endpoint for Imagen 4.0
      const genAIUrl = `https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict`;
      
      const requestBody = {
        instances: [
          {
            prompt: prompt,
          },
        ],
        parameters: {
          sampleCount: 1,
          aspectRatio: '1:1',
        },
      };

      const response = await axios.post(genAIUrl, requestBody, {
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': this.geminiApiKey,
        },
      });

      // Check response format - predictions array
      if (response.data?.predictions && response.data.predictions.length > 0) {
        const prediction = response.data.predictions[0];
        
        // Check for base64 encoded image
        if (prediction.bytesBase64Encoded) {
          return Buffer.from(prediction.bytesBase64Encoded, 'base64');
        }
        
        // Alternative format with mimeType
        if (prediction.mimeType && prediction.bytesBase64Encoded) {
          return Buffer.from(prediction.bytesBase64Encoded, 'base64');
        }
      }

      throw new Error('No image data in response');

    } catch (error: any) {
      console.error('Error generating image with Imagen API:', error.response?.data || error.message);
      
      // Provide helpful error messages
      if (error.response?.status === 404) {
        throw new Error('Imagen API endpoint not found. Please check your GEMINI_API_KEY and ensure it has access to Imagen API.');
      }
      
      if (error.response?.status === 401 || error.response?.status === 403) {
        throw new Error('Authentication failed. Please check your GEMINI_API_KEY is valid.');
      }
      
      throw new Error(`Failed to generate image: ${error.response?.data?.error?.message || error.message}`);
    }
  }

  /**
   * OLD HuggingFace implementation - commented out
   * Generate an image using HuggingFace API
   */
  /*
  async generateImageOld(prompt: string): Promise<Buffer> {
    try {
      const imageBlob = await this.client.textToImage({
        model: 'black-forest-labs/FLUX.1-dev',
        inputs: prompt,
        parameters: {
          num_inference_steps: 50,
          guidance_scale: 7.5,
          negative_prompt: 'blurry, low quality',
          width: 1024,
          height: 1024,
        },
      });

      if (typeof imageBlob === 'string') {
        const match = imageBlob.match(/^data:.+;base64,(.+)$/);
        if (match) {
          return Buffer.from(match[1], 'base64');
        }
        return Buffer.from(imageBlob, 'base64');
      }
      if (Buffer.isBuffer(imageBlob)) {
        return imageBlob;
      }
      if (
        imageBlob &&
        typeof imageBlob === 'object' &&
        typeof (imageBlob as any).arrayBuffer === 'function'
      ) {
        const arrayBuffer = await (imageBlob as any).arrayBuffer();
        return Buffer.from(arrayBuffer);
      }
      throw new Error('Unrecognized image response format');
    } catch (error) {
      console.error('Error generating image:', error);
      throw new Error('Failed to generate image');
    }
  }
  */

  /**
   * Generate a complete LinkedIn post with optional image
   */
  async generateLinkedInPostWithImage(
    topic: string,
    includeImage: boolean = false,
    language: string = 'en'
  ): Promise<{
    text: string;
    hashtags: string[];
    imagePrompt?: string;
    imageBuffer?: Buffer;
  }> {
    const post = await this.generateLinkedInPost(topic, true, language);
    
    if (includeImage) {
      const imagePrompt = await this.generateImagePrompt(topic);
      try {
        const imageBuffer = await this.generateImage(imagePrompt);
        return {
          ...post,
          imagePrompt,
          imageBuffer,
        };
      } catch (error) {
        console.error('Image generation failed, returning post without image:', error);
        return {
          ...post,
          imagePrompt,
        };
      }
    }

    return post;
  }
}

