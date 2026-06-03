/** GET /api/v1/health */
declare namespace Health {
  type HealthData = {
    api?: string;
    knowledge_service?: string;
  };
}
