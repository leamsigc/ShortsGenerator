<template>
  <naive-config>
    <NLoadingBarProvider>
      <NDialogProvider>
        <NNotificationProvider>
          <NMessageProvider>
            <NuxtLayout>
              <NuxtPage />
            </NuxtLayout>
            <NGlobalStyle />
          </NMessageProvider>
        </NNotificationProvider>
      </NDialogProvider>
    </NLoadingBarProvider>
  </naive-config>
</template>
