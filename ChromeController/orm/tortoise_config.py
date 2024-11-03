tortoise_config = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.postgresql",
            "credentials": {
                "host": "127.0.0.1",
                "port": 5432,
                "user": "repricer_manager",
                "password": "repricerpassword",
                "database": "repricer",
            },
        }
    },
    "apps": {
        "models": {
            "models": ["ChromeController.orm.models"],
            "default_connection": "default",
        },
    },
}

