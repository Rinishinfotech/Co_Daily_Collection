import axios from "axios";

const backendUrl = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: `${backendUrl}/api`,
  withCredentials: true,
});

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
    localStorage.setItem("ledgerflow_token", token);
  } else {
    delete api.defaults.headers.common.Authorization;
    localStorage.removeItem("ledgerflow_token");
  }
};

const savedToken = localStorage.getItem("ledgerflow_token");
if (savedToken) {
  api.defaults.headers.common.Authorization = `Bearer ${savedToken}`;
}

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