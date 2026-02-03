<script setup>

import {useRoute} from "vue-router";

const route = useRoute()
</script>

<template>
空间:{{route.params.user_id}}
</template>

<style scoped>

</style>