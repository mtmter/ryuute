import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  query,
  setDoc,
  updateDoc,
  where,
  writeBatch,
} from "firebase/firestore";
import { db } from "./firebase";

function userCollection(uid, collectionName) {
  return collection(db, "users", uid, collectionName);
}

function userDocument(uid, collectionName, documentId) {
  return doc(db, "users", uid, collectionName, String(documentId));
}

function dataWithId(documentSnapshot) {
  return {
    id: documentSnapshot.id,
    ...documentSnapshot.data(),
  };
}

async function getCollectionData(uid, collectionName) {
  const snapshot = await getDocs(userCollection(uid, collectionName));
  return snapshot.docs.map(dataWithId);
}

export async function loadScheduleData(uid) {
  const [events, tasks, preparations] = await Promise.all([
    getCollectionData(uid, "events"),
    getCollectionData(uid, "tasks"),
    getCollectionData(uid, "preparations"),
  ]);

  return { events, preparations, tasks };
}

export async function createEvent(uid, eventData) {
  const documentReference = await addDoc(
    userCollection(uid, "events"),
    eventData,
  );
  return { id: documentReference.id, ...eventData };
}

export async function updateEvent(uid, eventId, eventData) {
  await updateDoc(userDocument(uid, "events", eventId), eventData);
  return { id: String(eventId), ...eventData };
}

export async function deleteEvent(uid, eventId) {
  const batch = writeBatch(db);
  const preparationsSnapshot = await getDocs(
    query(
      userCollection(uid, "preparations"),
      where("event_id", "==", String(eventId)),
    ),
  );

  preparationsSnapshot.docs.forEach((preparationDocument) => {
    batch.delete(preparationDocument.ref);
  });
  batch.delete(userDocument(uid, "travelPlans", eventId));
  batch.delete(userDocument(uid, "events", eventId));
  await batch.commit();
}

export async function createTask(uid, taskData) {
  const documentData = { ...taskData, completed: false };
  const documentReference = await addDoc(
    userCollection(uid, "tasks"),
    documentData,
  );
  return { id: documentReference.id, ...documentData };
}

export async function updateTask(uid, taskId, taskData) {
  await updateDoc(userDocument(uid, "tasks", taskId), taskData);
  return { id: String(taskId), ...taskData };
}

export async function deleteTask(uid, taskId) {
  await deleteDoc(userDocument(uid, "tasks", taskId));
}

export async function createPreparation(uid, eventId, title) {
  const documentData = {
    event_id: String(eventId),
    title,
    completed: false,
  };
  const documentReference = await addDoc(
    userCollection(uid, "preparations"),
    documentData,
  );
  return { id: documentReference.id, ...documentData };
}

export async function updatePreparation(
  uid,
  preparationId,
  preparationData,
) {
  await updateDoc(
    userDocument(uid, "preparations", preparationId),
    preparationData,
  );
  return { id: String(preparationId), ...preparationData };
}

export async function deletePreparation(uid, eventId, preparationId) {
  const preparationDocument = userDocument(
    uid,
    "preparations",
    preparationId,
  );
  const snapshot = await getDoc(preparationDocument);
  if (
    !snapshot.exists() ||
    snapshot.data().event_id !== String(eventId)
  ) {
    throw new Error("準備項目が見つかりません");
  }
  await deleteDoc(preparationDocument);
}

export async function getTravelPlan(uid, eventId) {
  const snapshot = await getDoc(
    userDocument(uid, "travelPlans", eventId),
  );
  if (!snapshot.exists()) {
    return null;
  }
  return dataWithId(snapshot);
}

export async function saveTravelPlan(uid, eventId, route) {
  const documentData = {
    ...route,
    event_id: String(eventId),
  };
  await setDoc(
    userDocument(uid, "travelPlans", eventId),
    documentData,
  );
  return { id: String(eventId), ...documentData };
}
