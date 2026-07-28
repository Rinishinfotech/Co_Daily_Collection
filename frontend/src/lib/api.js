import axios from "axios";

const backendUrl = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: `${backendUrl}/api`,
});

export const currency = (amount) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount || 0);

export const dateTime = (value) =>
  new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));