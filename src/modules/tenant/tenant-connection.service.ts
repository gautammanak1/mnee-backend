import { Injectable, Logger } from '@nestjs/common';
import { Connection, createConnection } from 'mongoose';

@Injectable()
export class TenantConnectionService {
  private connections: Map<string, Connection> = new Map();
  private readonly logger = new Logger(TenantConnectionService.name);
  

  async getConnection(dbName: string): Promise<Connection> {
    console.log(dbName)
    if (this.connections.has(dbName)) {
      return this.connections.get(dbName)!;
    }

    const baseUri = process.env.MONGO_URI;
    if (!baseUri) {
      throw new Error('MONGO_URI environment variable is not defined');
    }
    const uri = baseUri.replace('sociantra', dbName);
    const conn = await createConnection(uri);
    this.connections.set(dbName, conn);
    this.logger.log(`🔗 Created new DB connection for ${dbName}`);
    return conn;
  }
}