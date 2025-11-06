// task.service.ts
import { Injectable } from '@nestjs/common';
import { TenantConnectionService } from '../tenant/tenant-connection.service';

import { Model } from 'mongoose';
import { TaskSchema } from '../tasks/schemas/task.schema';

@Injectable()
export class TaskService {
  constructor(private readonly tenantService: TenantConnectionService) {}

  private async getTenantModel(dbName: string): Promise<Model<any>> {
    const conn = await this.tenantService.getConnection(dbName);
    return conn.model('Task', TaskSchema);
  }

  async createTask(user: any, dto: any) {
    const model = await this.getTenantModel(user.dbName);
    return model.create({ ...dto, userId: user.userId });
  }

  async findAll(user: any) {
    const model = await this.getTenantModel(user.dbName);
    return model.find({ userId: user.userId });
  }

  async deleteTask(user: any, id: string) {
    const model = await this.getTenantModel(user.dbName);
    return model.findOneAndDelete({ _id: id, userId: user.userId });
  }
}
