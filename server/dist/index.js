"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const app = (0, express_1.default)();
app.use(express_1.default.json());
// In-memory store: userId -> pending messages
const signedInUsers = new Map();
// Sign in
app.post("/signin/:userId", (req, res) => {
    const userId = req.params["userId"];
    if (signedInUsers.has(userId)) {
        res.json({ message: `User ${userId} is already signed in` });
        return;
    }
    signedInUsers.set(userId, []);
    res.json({ message: `User ${userId} signed in` });
});
// Sign out
app.post("/signout/:userId", (req, res) => {
    const userId = req.params["userId"];
    if (!signedInUsers.has(userId)) {
        res.status(400).json({ message: `User ${userId} is not signed in` });
        return;
    }
    signedInUsers.delete(userId);
    res.json({ message: `User ${userId} signed out` });
});
// Post a message
app.post("/message/:senderId", (req, res) => {
    const senderId = req.params["senderId"];
    const receiver_id = req.body.receiver_id;
    const message_text = req.body.message_text;
    const current_timestamp = req.body.current_timestamp;
    if (!signedInUsers.has(senderId)) {
        res.status(400).json({ message: "user with this id is not signed in" });
        return;
    }
    const message = { sender_id: senderId, message_text, current_timestamp };
    if (signedInUsers.has(receiver_id)) {
        signedInUsers.get(receiver_id).push(message);
        res.json({ message: "Message delivered" });
    }
    else {
        res.json({ message: `Receiver ${receiver_id} is not signed in, message not delivered` });
    }
});
// Get messages for a user (clears inbox after reading)
app.get("/messages/:userId", (req, res) => {
    const userId = req.params["userId"];
    if (!signedInUsers.has(userId)) {
        res.status(400).json({ message: "user with this id is not signed in" });
        return;
    }
    const messages = signedInUsers.get(userId);
    signedInUsers.set(userId, []);
    res.json({ messages });
});
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
