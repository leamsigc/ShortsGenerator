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
const { currentRoute, replace } = useRouter();

const { params, query } = unref(currentRoute);
const { path, _redirect_type = "path" } = params;

Reflect.deleteProperty(params, "_redirect_type");
Reflect.deleteProperty(params, "path");

const _path = isArray(path) ? path.join("/") : path;

if (_redirect_type === "name") {
  replace({
    name: _path,
    query,
    params,
  });
} else {
  replace({
    path: _path.startsWith("/") ? _path : `/${_path}`,
    query,
  });
}
</script>

<template>
  <div />
</template>
<style scoped></style>
