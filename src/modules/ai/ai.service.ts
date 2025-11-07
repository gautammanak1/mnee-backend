import { Injectable } from '@nestjs/common';
import { GoogleGenerativeAI } from '@google/generative-ai';

import { InferenceClient } from '@huggingface/inference';

@Injectable()
export class AIService {
  private model: any;

  private client: InferenceClient;
  constructor() {
    if (!process.env.GEMINI_API_KEY) {
      throw new Error('GEMINI_API_KEY environment variable is not set');
    }
    if (!process.env.HF_API_TOKEN) {
      throw new Error('HF_API_TOKEN environment variable is not set');
    }
    this.client = new InferenceClient(process.env.HF_API_TOKEN);
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
    this.model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash-exp' });
    // For image generation, we'll use Gemini's image generation capabilities
    // Note: Gemini can generate images using the Imagen API or we can use a different service
    // For now, we'll use a text-to-image approach with Gemini's capabilities
  }

  /**
   * Generate a LinkedIn post based on a topic
   */
  async generateLinkedInPost(topic: string, includeHashtags: boolean = true): Promise<{
    text: string;
    hashtags: string[];
  }> {
    const prompt = `Generate a professional LinkedIn post about "${topic}". 

Requirements:
- The post should be engaging, professional, and valuable to LinkedIn audience
- Length should be between 150-300 words
- Include a hook in the first line to grab attention
- Add value with insights, tips, or thought-provoking questions
- End with a call-to-action or question to encourage engagement
- Make it sound natural and authentic, not robotic
- Use professional but conversational tone

${includeHashtags ? 'Also suggest 3-5 relevant hashtags for this post (return them as a comma-separated list).' : ''}

Format your response as JSON:
{
  "text": "the post content here",
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

      return {
        text: parsed.text || response,
        hashtags: parsed.hashtags || [],
      };
    } catch (error) {
      console.error('Error generating LinkedIn post:', error);
      throw new Error('Failed to generate LinkedIn post');
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
   * Generate an image using an external service
   * Note: Gemini doesn't directly generate images, so we'll use a text-to-image API
   * 
   * Supported services:
   * - Stability AI (Stable Diffusion) - Set IMAGE_API_TYPE=stability
   * - OpenAI DALL-E - Set IMAGE_API_TYPE=dalle
   * - Hugging Face - Set IMAGE_API_TYPE=huggingface
   * 
   * Environment variables needed:
   * - IMAGE_GENERATION_API_KEY: Your API key
   * - IMAGE_API_TYPE: Type of service (stability, dalle, huggingface)
   */
  async generateImage(prompt: string): Promise<Buffer> {
   
  
    try {
      const imageBlob = await this.client.textToImage({
        model: 'black-forest-labs/FLUX.1-dev',
        inputs: prompt,
        parameters: {
          num_inference_steps: 50, // Higher for better quality (default: 50)
          guidance_scale: 7.5,     // Controls prompt adherence (default: 7.5)
          negative_prompt: 'blurry, low quality', // Optional: What to avoid
          width: 1024,             // Optional: Image dimensions
          height: 1024,
        },
      });

      // Convert image string (base64 or URL) to Buffer
      if (typeof imageBlob === 'string') {
        // Assume the service returns a base64-encoded image string (e.g. "data:image/png;base64,...")
        const match = imageBlob.match(/^data:.+;base64,(.+)$/);
        if (match) {
          return Buffer.from(match[1], 'base64');
        }
        // If it's a direct base64 string (not prefixed)
        return Buffer.from(imageBlob, 'base64');
      }
      // If by some library contract it actually is a Buffer (rare)
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

    }
    catch (error) {
      console.error('Error generating image:', error);
      throw new Error('Failed to generate image');
    }
  }

  /**
   * Generate a complete LinkedIn post with optional image
   */
  async generateLinkedInPostWithImage(
    topic: string,
    includeImage: boolean = false
  ): Promise<{
    text: string;
    hashtags: string[];
    imagePrompt?: string;
    imageBuffer?: Buffer;
  }> {
    const post = await this.generateLinkedInPost(topic, true);
    
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

