# Message endpoint format

### Message object

| Field | Type | Description |
|---|---|---|
| from_name | String | Will be used in the `From:` field when sending an email.
| from_email | String | Will be used in the `From:` field when sending an email.
| recipients | Array of recipient objects | One or more recipients.
| contents | Array of content objects | One or more contents

#### Recipient objects

| Field | Type | Description |
|---|---|---|
| uuid | UUID string | Uuid of the user whose contact information will be used 
| email | Email string | The `To:` field when sending an email.

Either `uuid` or `email` is required. If the `uuid` is supplied, the messaging service will query contact details from Tunnistamo.

#### Content objects

| Field | Type | Description |
|---|---|---|
| language | String | ISO 639-1 language code. Currently used languages are: `fi`, `sv`, `en` 
| subject | String | The `Subject:` field when sending an email.
| text | String | The text version of an email
| html | String | The html version of an email
| short_text | String | The SMS / notification popup version of the message

- The language field is not required. Default language is `fi`.
- There can be multiple contents in multiple languages. The first content in the users language is used. If the users language is not defined (e.g. only email address provided) the default language is `fi`.
- If there is no content in the users language, the first existing language in the following order is used: `fi`, `sv`, `en`

## Example JSON

    {
        "from_name": "John Doe",
        "from_email": "john@example.com",
        "recipients": [
            {
                "uuid": "f4b9777e-7b3d-11e7-b8f0-186590cf27c7"
            },
            {
                "uuid": "711c52eb-805a-41be-a61d-02547ecf12e8"
            },
            {
                "email": "third@example.com"
            }
        ],
        "contents": [
            {
                "language": "fi",
                "subject": "Test subject fi",
                "text": "Test text fi",
                "html": "<p>Test html fi</p>",
                "short_text": "Test short text fi"
            },
            {
                "language": "sv",
                "subject": "Test subject sv",
                "text": "Test text sv",
                "html": "<p>Test html sv</p>",
                "short_text": "Test short text sv"
            }
        ]
    
