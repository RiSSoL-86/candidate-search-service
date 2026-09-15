import copy
import json
from typing import Any

ARN = "arn:aws:sqs:us-east-1:440427555138:candidate-search-service-ingest"


class Context:
    """The parts of the Lambda context Powertools puts in every log line."""

    function_name = "candidate-search-service-database-ingest"
    memory_limit_in_mb = 512
    invoked_function_arn = ARN.replace("sqs", "lambda")
    aws_request_id = "3f2a1b0c"

    def get_remaining_time_in_millis(self) -> int:
        return 30_000


RESUME: dict[str, Any] = {
    "id": "002b134f0010fee16600261bcc424743354b70",
    "real_id": "285139302",
    "owner": {"id": "171538711", "comments": {"counters": {"total": 0}}},
    "url": "https://api.hh.ru/resumes/002b134f",
    "alternate_url": "https://hh.ru/resume/002b134f",
    "created_at": "2025-03-01T10:00:00+03:00",
    "updated_at": "2026-09-01T10:00:00+03:00",
    "platform": {"id": "headhunter"},
    "title": "Финансовый аналитик",
    "salary": {"amount": 350000, "currency": "RUR"},
    "total_experience": {"months": 22},
    "skill_set": ["SQL", "Python"],
    "skills": "Свободный английский",
    "photo": {"small": "https://img.hhcdn.ru/photo/1.jpeg"},
    "area": {"id": "1", "name": "Москва", "url": "https://api.hh.ru/areas/1"},
    "metro": {
        "id": "14.195",
        "name": "Горьковская",
        "lat": 59.984947,
        "lng": 30.344259,
        "order": 5,
        "line": {"id": "14", "name": "Московско-Петроградская"},
    },
    "age": 22,
    "gender": {"id": "male", "name": "Мужчина"},
    "birth_date": "2003-09-09",
    "contact": [{"type": {"id": "cell"}, "value": {"formatted": "hidden"}}],
    "relocation": {
        "type": {"id": "no_relocation"},
        "area": [],
        "district": [],
    },
    "driver_license_types": [{"id": "B"}],
    "has_vehicle": False,
    "schedules": [{"id": "remote", "name": "Удалённая работа"}],
    "education": {
        "level": {"id": "bachelor", "name": "Бакалавр"},
        "primary": [
            {
                "id": "104370424",
                "name": "МГУ",
                "organization": "Экономический факультет",
                "result": None,
                "year": 2026,
                "university_acronym": "МГУ",
                "name_id": "47497",
                "education_level": {"id": "bachelor"},
            }
        ],
        "additional": [
            {"id": "26947561", "name": "Python", "organization": "GeekBrains"}
        ],
        "attestation": [],
        "elementary": [],
    },
    "experience": [
        {
            "id": "2102112235",
            "start": "2024-11-01",
            "end": None,
            "company": "Lod Capital",
            "company_id": None,
            "company_url": None,
            "employer": None,
            "position": "Финансовый аналитик",
            "description": "Управление рисками",
            "area": None,
            "industry": None,
            "industries": [],
        },
        {
            "id": "2102112236",
            "start": "2023-01-01",
            "end": "2024-10-01",
            "company": "Ростелеком",
            "company_id": "1826011",
            "employer": {
                "id": "5390761",
                "name": "Ростелеком",
                "url": "https://api.hh.ru/employers/5390761",
                "alternate_url": "https://hh.ru/employer/5390761",
                "logo_urls": {"90": "https://img.hhcdn.ru/logo/1.png"},
            },
            "position": "Аналитик",
            "area": {
                "id": "88",
                "name": "Казань",
                "url": "https://api.hh.ru/areas/88",
            },
        },
    ],
}


def envelope(
    key: str = "full_resumes_hh/002b134f.json",
    version_id: str | None = "5jK3xQ",
    **resume: Any,
) -> dict[str, Any]:
    """A Lambda payload for the sample resume, patched field by field."""
    payload = copy.deepcopy(RESUME)
    payload.update(resume)

    return {
        "source": {
            "bucket": "candidate-search-service-resumes",
            "key": key,
            "version_id": version_id,
            "downloaded_at": "2026-09-14T12:00:00+00:00",
            "resume_type": "full",
        },
        "resume": payload,
    }


def sqs_event(*bodies: dict[str, Any]) -> dict[str, Any]:
    """A batch as SQS hands it over, one message per envelope."""
    return {
        "Records": [
            {
                "messageId": f"message-{number}",
                "receiptHandle": f"handle-{number}",
                "body": json.dumps(body),
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "1789200000000",
                    "SenderId": "AIDAIENQZJOLO23YVJ4VO",
                    "ApproximateFirstReceiveTimestamp": "1789200000100",
                },
                "messageAttributes": {},
                "md5OfBody": "",
                "eventSource": "aws:sqs",
                "eventSourceARN": ARN,
                "awsRegion": "us-east-1",
            }
            for number, body in enumerate(bodies)
        ]
    }
