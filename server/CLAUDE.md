# Server discription

This is the server for realtime messaging application.

The server must be written in typescript, use express, and save information in memory.

It should have the following functionality:

Everything is saved in the memory, no database

- Sign in
    - subscript and listen for the messages with my id
- Sign out
    - unsubscribe from the messages

- Post a message which takes parameters: 
    - receiver_id: string
    - message_text: string
    - current_timestamp: date
    - it should check if the user is signed in, if not return a message "user with this id is not signed in"
    - if the reciever user is sigend it it should deliver the message
