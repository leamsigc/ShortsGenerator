<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

/*----------  Toggle button  ----------*/
const { t } = useI18n();

/*----------  FullScreen  ----------*/
const { toggle: toggleFullScreen } = useFullscreen();
</script>
<template>
  <div class="flex h-16 items-center <lg:justify-end">
    <div class="md:block px-4"></div>
    <div class="flex-1 <lg:hidden"></div>
    <div class="flex flex-grow-1 items-center <2xl:hidden">
      <LayoutTabs />
    </div>
    <div class="flex">
      <NSpace>
        <SearchTrigger />
        <div class="flex items-center justify-center">
          <NSpace>
            <ActionIcon
              :tooltip-text="t('layouts.header.toggleFullScreen')"
              icon="i-tabler-maximize"
              @click="toggleFullScreen"
            />
            <NaiveColorModeSwitch size="large" class="pt-1" />
          </NSpace>
        </div>
      </NSpace>
    </div>
  </div>
</template>

<style scoped></style>
