async (page) => {
  const demo = {
    meta: {dataset_id:'browser-test-only',source:'synthetic browser verification',month:null,real_order_data:false,synthetic_warehouse:true,cell_size_m:1.5},
    layout:{layout_id:'original',width:4,height:3,walkable_cells:[[0,0],[1,0],[2,0],[3,0]],dock:[0,0],slots:[{slot_id:'S001',rack_cell:[1,1],access_cell:[1,0],sku:'B'},{slot_id:'S002',rack_cell:[3,1],access_cell:[3,0],sku:'A'}]},
    products:[{sku:'A',name:'Fast item',pick_frequency:9},{sku:'B',name:'Slow item',pick_frequency:1}],
    orders:[{order_id:'O1',lines:[{sku:'A',quantity:1}]}]
  };
  const calls=[];
  await page.route('**/api/demo', route => route.fulfill({json:demo}));
  await page.route('**/api/simulate', async route => {
    const body=route.request().postDataJSON(); calls.push(body);
    const assignments=body.policy==='original'?{S001:'B',S002:'A'}:body.policy==='baseline'?{S001:'A',S002:'B'}:body.slot_assignments;
    const near=assignments.S001==='A';
    const points=near?[[0,0],[1,0],[0,0]]:[[0,0],[1,0],[2,0],[3,0],[2,0],[1,0],[0,0]];
    const distance=near?3:9;
    const time=distance/1.2+10;
    await route.fulfill({json:{dataset_id:demo.meta.dataset_id,policy:body.policy,slot_assignments:assignments,orders_replayed:1,distance_m:distance,estimated_pick_time_s:time,average_pick_time_s:time,routes:[{order_id:'O1',waypoints:points,visits:[{sku:'A',slot_id:near?'S001':'S002',waypoint_index:near?1:3}]}],warnings:[],assumptions:{speed_mps:1.2,handling_seconds_per_line:10}}});
  });
  await page.reload();
  await page.getByText('Simulation connected',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Replay & compare',exact:true}).click();
  await page.getByRole('button',{name:'Inspect original route'}).waitFor();
  if(calls.length!==3)throw new Error('Expected three policy requests');
  if(calls.some(c=>JSON.stringify(c.order_ids)!=='["O1"]'||c.speed_mps!==1.2))throw new Error('Mismatched replay selection/speed');
  const first=JSON.stringify(calls[0].slot_assignments);
  if(calls.some(c=>JSON.stringify(c.slot_assignments)!==first))throw new Error('Request assignments were not snapshotted');
  await page.getByRole('button',{name:'Inspect baseline route'}).click();
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.getByRole('button',{name:'Pause',exact:true}).waitFor();
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.getByRole('button',{name:'Reset replay',exact:true}).click();
  await page.getByRole('button',{name:'S001 Slow item',exact:true}).click();
  await page.getByRole('button',{name:'S002 Fast item',exact:true}).click();
  if(await page.getByRole('button',{name:'Inspect original route'}).count())throw new Error('Stale comparison survived slot swap');
  await page.getByRole('button',{name:'S001 Fast item',exact:true}).waitFor();
  await page.getByRole('button',{name:'Replay & compare',exact:true}).click();
  await page.getByRole('button',{name:'Inspect player route'}).waitFor();
  if(calls.length!==6||calls[5].slot_assignments.S001!=='A')throw new Error('Swapped mapping not submitted');
  await page.getByRole('button',{name:'Top view',exact:true}).click();
  await page.getByRole('button',{name:'Orders',exact:true}).click();
  await page.getByText('O1',{exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  if(overflow)throw new Error('Mobile horizontal overflow');
  return 'PASS: synthetic API contract flow, identical replay inputs, policy switching, pause/reset, swaps clear stale results, new mapping submitted, orders tab, top view, mobile width. Not real backend verification.';
}
