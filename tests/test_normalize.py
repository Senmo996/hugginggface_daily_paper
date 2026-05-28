from hf_daily.normalize import normalize_daily_response


def test_normalizes_hugging_face_daily_response():
    raw = [
        {
            "paper": {
                "id": "2605.28820",
                "title": "From Pixels to Words -- Towards Native One-Vision Models at Scale",
                "summary": "Current vision-language models stitch together separate encoders.",
                "authors": [
                    {"name": "Haiwen Diao"},
                    {"name": "Jiahao Wang"},
                    {"name": "Penghao Wu"},
                ],
                "publishedAt": "2026-05-27T00:00:00.000Z",
                "submittedOnDailyAt": "2026-05-28T00:00:00.000Z",
                "upvotes": 39,
                "ai_keywords": ["vision-language models", "native VLMs"],
                "projectPage": "https://github.com/EvolvingLMMs-Lab/NEO",
                "githubRepo": "https://github.com/EvolvingLMMs-Lab/NEO",
                "organization": {
                    "name": "UIUC-CS",
                    "fullname": "University of Illinois at Urbana-Champaign",
                },
            },
            "numComments": 2,
            "thumbnail": "https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2605.28820.png",
        }
    ]

    papers = normalize_daily_response(raw, daily_date="2026-05-28")

    assert papers == [
        {
            "id": "2605.28820",
            "daily_date": "2026-05-28",
            "title": "From Pixels to Words -- Towards Native One-Vision Models at Scale",
            "summary": "Current vision-language models stitch together separate encoders.",
            "authors": ["Haiwen Diao", "Jiahao Wang", "Penghao Wu"],
            "published_at": "2026-05-27T00:00:00.000Z",
            "submitted_on_daily_at": "2026-05-28T00:00:00.000Z",
            "upvotes": 39,
            "num_comments": 2,
            "ai_keywords": ["vision-language models", "native VLMs"],
            "institution": "University of Illinois at Urbana-Champaign",
            "hf_url": "https://huggingface.co/papers/2605.28820",
            "arxiv_url": "https://arxiv.org/abs/2605.28820",
            "project_page": "https://github.com/EvolvingLMMs-Lab/NEO",
            "github_repo": "https://github.com/EvolvingLMMs-Lab/NEO",
            "thumbnail": "https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2605.28820.png",
        }
    ]


def test_normalizes_powershell_wrapped_array_response():
    raw = {
        "value": [
            {
                "paper": {
                    "id": "2605.27762",
                    "title": "PEAM: Parametric Embodied Agent Memory",
                    "summary": "We present PEAM.",
                    "authors": [{"name": "Yuchen Guo"}],
                }
            }
        ],
        "Count": 1,
    }

    papers = normalize_daily_response(raw, daily_date="2026-05-28")

    assert papers[0]["id"] == "2605.27762"
    assert papers[0]["institution"] is None
    assert papers[0]["num_comments"] == 0
