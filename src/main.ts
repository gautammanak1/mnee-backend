import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';
import * as cookieParser from 'cookie-parser';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.use(cookieParser());
  app.enableCors({
    origin: '*',
    credentials: true,
  });

  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));

  // ✅ Swagger setup with JWT bearer auth
  const config = new DocumentBuilder()
    .setTitle('Sociantra API Docs')
    .setDescription('API documentation for the Sociantra social automation backend')
    .setVersion('1.0')
    .addBearerAuth(
      {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
        name: 'Authorization',
        description: 'Enter JWT token (without "Bearer " prefix)',
        in: 'header',
      },
      'access-token', // custom name for reference
    )
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document, {
    swaggerOptions: {
      persistAuthorization: true,
      tagsSorter: 'alpha',
      operationsSorter: 'method',
    },
  });

  const port = process.env.PORT || 5000;
  await app.listen(port);
  console.log(`✅ Sociantra API running on http://localhost:${port}`);
  console.log(`📘 Swagger Docs: http://localhost:${port}/api/docs`);
}

bootstrap();
