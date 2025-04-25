from locust import HttpUser, task, between

class ChatCompletionsUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def chat_completion(self):
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello!"}]
        }
        headers = {"Authorization": "Bearer KJCaKhC3cTNUS3J2DUVhZxsdV9JDCcOLD7BbjvCc"}
        self.client.post("/v1/chat/completions", json=payload, headers=headers)
