import { Injectable, NotFoundException } from '@nestjs/common';
import { Inject } from '@nestjs/common';
import { Model } from 'mongoose';

import { Task, TaskSchema } from './schemas/task.schema';
import { TenantConnectionService } from '../tenant/tenant-connection.service';


@Injectable()
export class TasksService {
constructor(
    private readonly tenantService: TenantConnectionService,

) {}
  private async getTenantModel(dbName: string): Promise<Model<any>> {
    const conn = await this.tenantService.getConnection(dbName);
    return conn.model('Task', TaskSchema);
  }

async createTask(userId: string, dbName: string, dto: any) {
const model = await this.getTenantModel(dbName);
const task = new model({ userId, ...dto, status: 'draft' });
return task.save();
}


async getAllTasks(userId: string) {
const model = await this.getTenantModel(userId);
return model.find({ userId }).sort({ createdAt: -1 });
}


async getTaskById(userId: string, id: string) {
const model = await this.getTenantModel(userId);
const task = await model.findOne({ _id: id, userId });
if (!task) throw new NotFoundException('Task not found');
return task;
}


async updateTask(userId: string, id: string, dto: any) {
const model = await this.getTenantModel(userId);
const task = await model.findOneAndUpdate({ _id: id, userId }, dto, { new: true });
if (!task) throw new NotFoundException('Task not found');
return task;
}


async deleteTask(userId: string, id: string) {
const model = await this.getTenantModel(userId);
const task = await model.findOneAndDelete({ _id: id, userId });
if (!task) throw new NotFoundException('Task not found');
return { message: 'Task deleted successfully' };
}
}