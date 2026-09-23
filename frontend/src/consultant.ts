export interface ConsultantBlock {
  title: string;
  explanation: string;
}

export interface ConsultantResponse {
  answer: string;
  strengths: ConsultantBlock[];
  risks: ConsultantBlock[];
  recommendations: ConsultantBlock[];
  follow_up_question: string | null;
}

export interface ConsultantClient {
  sendMessage(message: string): Promise<ConsultantResponse>;
}

// Replaced by a same-origin Python backend adapter when its chat route is published.
export const demoConsultantClient: ConsultantClient = {
  async sendMessage(_message) {
    return {
      answer: "Это макет ответа. Основной Python backend пока не предоставляет маршрут чата; сообщение не было отправлено AI-агенту.",
      strengths: [{ title: "Структура ответа", explanation: "Здесь появятся сильные стороны выбранного плана, подтверждённые AI-консультантом." }],
      risks: [{ title: "Риски", explanation: "Здесь будут конкретные риски и ограничения плана." }],
      recommendations: [{ title: "Следующий шаг", explanation: "После подключения маршрута чата этот блок покажет рекомендации из ответа сервера." }],
      follow_up_question: null,
    };
  },
};
