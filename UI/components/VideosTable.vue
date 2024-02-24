<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <Leamsigc>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

import "tabulator-tables/dist/css/tabulator.min.css";
import {
  TabulatorFull as Tabulator,
  type ColumnDefinition,
} from "tabulator-tables";
const table = ref(null); //reference to your table element
const tabulator = ref<Tabulator | null>(null); //variable to hold your table

const columns = ref<ColumnDefinition[]>([
  { title: "Name", field: "name", width: 150 },
  { title: "Age", field: "age", hozAlign: "left", formatter: "progress" },
  { title: "Favourite Color", field: "col" },
  { title: "Date Of Birth", field: "dob", hozAlign: "center" },
  { title: "Rating", field: "rating", hozAlign: "left", formatter: "star" },
  {
    title: "Passed?",
    field: "passed",
    hozAlign: "center",
    formatter: "tickCross",
  },
]);
const data = ref<Record<string, any>[]>([
  { id: 1, name: "Oli Bob", age: "12", col: "red", dob: "" },
  { id: 2, name: "Mary May", age: "1", col: "blue", dob: "14/05/1982" },
  {
    id: 3,
    name: "Christine Lobowski",
    age: "42",
    col: "green",
    rating: "5",
    dob: "22/05/1982",
  },
]);

onMounted(() => {
  if (!table.value) return;
  tabulator.value = new Tabulator(table.value, {
    data: data.value, //link data to table
    reactiveData: true, //enable data reactivity
    columns: columns.value, //define table columns
    layout: "fitDataStretch",
  });

  // Set time out and create a mock promise
  setTimeout(() => {
    console.log("set timeout");

    const response = [
      {
        id: 4,
        name: "Brendon Philips",
        age: "125",
        col: "orange",
        dob: "01/08/1980",
      },
      {
        id: 5,
        name: "Margret Marmajuke",
        age: "16",
        col: "yellow",
        dob: "31/01/1999",
      },
    ];
    response.forEach((item) => {
      data.value.push(item);
    });
  }, 5000);
});
</script>

<template>
  <div class="max-w-screen-xl w-full">
    <h3>Table here</h3>
    <div ref="table"></div>
  </div>
</template>
<style scoped></style>
