import express, { Request, Response } from "express";

const app = express();
app.use(express.json());

interface Message {
  sender_id: string;
  message_text: string;
  current_timestamp: string;
}

// In-memory store: userId -> pending messages
const signedInUsers = new Map<string, Message[]>();

// Sign in
app.post("/signin/:userId", (req: Request, res: Response) => {
  const userId = req.params["userId"] as string;
  if (signedInUsers.has(userId)) {
    res.json({ message: `User ${userId} is already signed in` });
    return;
  }
  signedInUsers.set(userId, []);
  res.json({ message: `User ${userId} signed in` });
});

// Sign out
app.post("/signout/:userId", (req: Request, res: Response) => {
  const userId = req.params["userId"] as string;
  if (!signedInUsers.has(userId)) {
    res.status(400).json({ message: `User ${userId} is not signed in` });
    return;
  }
  signedInUsers.delete(userId);
  res.json({ message: `User ${userId} signed out` });
});

// Post a message
app.post("/message/:senderId", (req: Request, res: Response) => {
  const senderId = req.params["senderId"] as string;
  const receiver_id = req.body.receiver_id as string;
  const message_text = req.body.message_text as string;
  const current_timestamp = req.body.current_timestamp as string;

  if (!signedInUsers.has(senderId)) {
    res.status(400).json({ message: "user with this id is not signed in" });
    return;
  }

  const message: Message = { sender_id: senderId, message_text, current_timestamp };

  if (signedInUsers.has(receiver_id)) {
    signedInUsers.get(receiver_id)!.push(message);
    res.json({ message: "Message delivered" });
  } else {
    res.json({ message: `Receiver ${receiver_id} is not signed in, message not delivered` });
  }
});

// Get messages for a user (clears inbox after reading)
app.get("/messages/:userId", (req: Request, res: Response) => {
  const userId = req.params["userId"] as string;
  if (!signedInUsers.has(userId)) {
    res.status(400).json({ message: "user with this id is not signed in" });
    return;
  }
  const messages = signedInUsers.get(userId)!;
  signedInUsers.set(userId, []);
  res.json({ messages });
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
