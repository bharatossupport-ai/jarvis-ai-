"""Connector SDK: each integration is a small class that registers typed tools."""
import requests
from security.policy import Risk
from tools.registry import REGISTRY, Tool

CONNECTORS = {}


class Connector:
    name = "base"
    description = ""
    tools = []  # tool names this connector adds

    def __init__(self, settings):
        self.settings = settings

    def enabled(self):
        return self.name in (self.settings.get("enabled_connectors") or [])

    def register(self):
        raise NotImplementedError


def connector(cls):
    CONNECTORS[cls.name] = cls
    return cls


@connector
class WeatherConnector(Connector):
    name = "weather"
    description = "Current weather from open-meteo.com (free, no key)"
    tools = ["weather_now"]

    def register(self):
        def weather_now(city: str):
            geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                               params={"name": city, "count": 1}, timeout=10).json()
            if not geo.get("results"):
                raise ValueError(f"City not found: {city}")
            g = geo["results"][0]
            w = requests.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": g["latitude"], "longitude": g["longitude"], "current_weather": True}, timeout=10).json()
            return {"place": f"{g['name']}, {g.get('country', '')}", **w["current_weather"]}
        REGISTRY.register(Tool("weather_now", "Current weather for a city", {"city": str}, Risk.LOW, weather_now))


@connector
class WebhookConnector(Connector):
    name = "webhook"
    description = "POST a message to a webhook URL you configure (e.g. Discord, Slack incoming webhook)"
    tools = ["send_webhook"]

    def register(self):
        def send_webhook(text: str):
            url = self.settings.get("webhook_url")
            if not url:
                raise ValueError("Set a webhook URL in Settings first.")
            r = requests.post(url, json={"content": text, "text": text}, timeout=10)
            r.raise_for_status()
            return "Sent"
        REGISTRY.register(Tool("send_webhook", "Send a message to your configured webhook", {"text": str},
                               Risk.EXTERNAL, send_webhook, lambda a: f"SEND to webhook:\n{a['text']}"))


def load_connectors(settings):
    active = []
    for cls in CONNECTORS.values():
        c = cls(settings)
        if c.enabled():
            c.register()
            active.append(c)
    return active
