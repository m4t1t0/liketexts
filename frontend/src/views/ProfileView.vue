<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ApiError } from "../api/client";
import Avatar from "../components/Avatar.vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

const firstName = ref("");
const lastName = ref("");
const saving = ref(false);
const saveMessage = ref("");
const profileError = ref("");

const selectedFile = ref<File | null>(null);
const previewUrl = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);

const ACCEPT = "image/png,image/jpeg,image/webp,image/gif";

const displayName = computed(() => auth.profile?.display_name ?? "");

onMounted(async () => {
  try {
    if (!auth.profile) await auth.fetchProfile();
    firstName.value = auth.profile?.first_name ?? "";
    lastName.value = auth.profile?.last_name ?? "";
  } catch (e) {
    profileError.value = e instanceof ApiError ? e.message : "Failed to load profile";
  }
});

async function saveNames(): Promise<void> {
  saveMessage.value = "";
  profileError.value = "";
  saving.value = true;
  try {
    // A picked-but-not-yet-uploaded picture is part of "changes" too —
    // upload it first so it can't be silently dropped on navigation.
    if (selectedFile.value) await uploadSelectedFile();
    await auth.updateProfile({
      first_name: firstName.value,
      last_name: lastName.value,
    });
    saveMessage.value = "Profile saved.";
  } catch (e) {
    profileError.value = e instanceof ApiError ? e.message : "Failed to save profile";
  } finally {
    saving.value = false;
  }
}

function onFileChange(event: Event): void {
  saveMessage.value = "";
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  selectedFile.value = file;
  previewUrl.value = file ? URL.createObjectURL(file) : null;
}

function clearSelection(): void {
  selectedFile.value = null;
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = null;
  if (fileInput.value) fileInput.value.value = "";
}

async function uploadSelectedFile(): Promise<void> {
  if (!selectedFile.value) return;
  uploading.value = true;
  try {
    await auth.uploadAvatar(selectedFile.value);
    clearSelection();
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <div class="mx-auto max-w-md space-y-8">
    <h1 class="text-2xl font-bold">Profile</h1>

    <p v-if="profileError" class="text-sm text-red-600">{{ profileError }}</p>

    <template v-if="auth.profile">
      <!-- Avatar -->
      <section class="space-y-3">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-stone-500">
          Profile picture
        </h2>
        <div class="flex items-center gap-4">
          <Avatar
            :name="displayName || '?'"
            :avatar-url="previewUrl ?? auth.profile.avatar_url"
            size="h-20 w-20"
          />
          <div class="text-sm text-stone-500">
            <p>PNG, JPG, WebP or GIF, max 2 MB.</p>
            <p>Pick a file, then press “Save changes”.</p>
          </div>
        </div>
        <input
          id="avatar-file"
          ref="fileInput"
          type="file"
          :accept="ACCEPT"
          class="hidden"
          @change="onFileChange"
        />
        <div class="flex items-center gap-3">
          <label
            for="avatar-file"
            class="cursor-pointer rounded border border-stone-300 bg-white px-3 py-1.5 text-sm hover:bg-stone-100"
          >
            Choose picture
          </label>
          <span class="truncate text-sm text-stone-500">
            {{ selectedFile ? selectedFile.name : "No file selected" }}
          </span>
        </div>
      </section>

      <!-- Names -->
      <section class="space-y-3">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-stone-500">
          Name
        </h2>
        <div class="grid grid-cols-2 gap-3">
          <input
            v-model="firstName"
            placeholder="First name"
            maxlength="120"
            class="w-full rounded border border-stone-300 px-3 py-2"
          />
          <input
            v-model="lastName"
            placeholder="Last name"
            maxlength="120"
            class="w-full rounded border border-stone-300 px-3 py-2"
          />
        </div>
        <p v-if="saveMessage" class="text-sm text-green-700">{{ saveMessage }}</p>
        <button
          :disabled="saving || uploading"
          class="rounded bg-stone-900 px-4 py-2 text-sm text-white hover:bg-stone-700 disabled:opacity-50"
          @click="saveNames"
        >
          {{ saving || uploading ? "Saving…" : "Save changes" }}
        </button>
      </section>
    </template>
  </div>
</template>
