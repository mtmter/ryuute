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

const API_BASE_URL = import.meta.env.VITE_BACKEND_API_BASE_URL;
const LOCAL_MIGRATION_STORAGE_KEY = "ryuute_local_sqlite_migrated";

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

function withoutId(data) {
  const documentData = { ...data };
  delete documentData.id;
  return documentData;
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

async function fetchLegacyData(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error("SQLiteの既存データを読み込めませんでした");
  }
  return response.json();
}

async function fetchLegacyTravelPlan(eventId) {
  const response = await fetch(
    `${API_BASE_URL}/events/${eventId}/travel-plan`,
  );
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error("SQLiteの移動予定を読み込めませんでした");
  }
  return response.json();
}

function isLocalMigrationComplete() {
  try {
    return window.localStorage.getItem(LOCAL_MIGRATION_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function rememberLocalMigration() {
  try {
    window.localStorage.setItem(LOCAL_MIGRATION_STORAGE_KEY, "true");
  } catch {
    // Firestore側にも完了記録があるため、localStorageが使えなくても続行します。
  }
}

export async function migrateLocalDataIfNeeded(uid) {
  const migrationDocument = userDocument(
    uid,
    "metadata",
    "localSqliteMigration",
  );
  const migrationSnapshot = await getDoc(migrationDocument);

  if (migrationSnapshot.exists()) {
    rememberLocalMigration();
    return;
  }

  // SQLiteのデータは最初にログインした1ユーザーへだけ移行します。
  if (isLocalMigrationComplete()) {
    return;
  }

  const [events, tasks, preparations] = await Promise.all([
    fetchLegacyData("/events"),
    fetchLegacyData("/tasks"),
    fetchLegacyData("/preparations"),
  ]);
  const travelPlans = (
    await Promise.all(
      events.map((event) => fetchLegacyTravelPlan(event.id)),
    )
  ).filter(Boolean);

  const batch = writeBatch(db);
  events.forEach((event) => {
    batch.set(
      userDocument(uid, "events", event.id),
      withoutId(event),
    );
  });
  tasks.forEach((task) => {
    batch.set(
      userDocument(uid, "tasks", task.id),
      withoutId(task),
    );
  });
  preparations.forEach((preparation) => {
    batch.set(
      userDocument(uid, "preparations", preparation.id),
      {
        ...withoutId(preparation),
        event_id: String(preparation.event_id),
      },
    );
  });
  travelPlans.forEach((travelPlan) => {
    batch.set(
      userDocument(uid, "travelPlans", travelPlan.event_id),
      {
        ...withoutId(travelPlan),
        event_id: String(travelPlan.event_id),
      },
    );
  });
  batch.set(migrationDocument, {
    completed_at: new Date().toISOString(),
  });

  await batch.commit();
  rememberLocalMigration();
}
