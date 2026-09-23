import { cityApi, type ChatMessage, type ConsultantResponse, type UUID } from "./cityApi";

export type { ChatMessage, ConsultantBlock, ConsultantResponse } from "./cityApi";

export interface ConsultantClient {
  sendMessage(message: string, signal?: AbortSignal): Promise<ConsultantResponse>;
  getMessages(signal?: AbortSignal): Promise<ChatMessage[]>;
}

/** Browser talks only to the trusted Python backend; it never calls the AI service. */
export function createConsultantClient(scenarioId: UUID): ConsultantClient {
  return {
    sendMessage: (message, signal) => cityApi.sendChatMessage(scenarioId, message, signal),
    getMessages: (signal) => cityApi.getChatMessages(scenarioId, signal),
  };
}
