\ Model PassengerReallocation
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  150 t_1^0 + 170 t_2^0 + 80 t_3^0 + 70 t_4^0 + 50 t_5^0 + 120 t_6^0
   + 100 t_7^0 + 100 t_8^0 + 140 t_9^0 + 80 t_10^0 + 150 t_11^0
   + 180 t_12^0 + 100 t_13^0 + 75 t_14^0 + 80 t_15^0 + 155 t_2^1 + 66 t_3^4
   + 165 t_12^11
Subject To
 Flight_101_Capacity: t_6^0 + t_13^0 >= 42
 Flight_102_Capacity: t_1^0 + t_7^0 >= 62
 Flight_104_Capacity: t_2^0 + t_8^0 >= 82
 Flight_201_Capacity: t_5^0 + t_7^0 + t_11^0 >= 36
 Flight_202_Capacity: t_3^0 + t_10^0 + t_13^0 >= 117
 Flight_203_Capacity: t_8^0 + t_12^0 >= 142
 Flight_204_Capacity: t_4^0 >= -8
 Flight_301_Capacity: t_10^0 + t_14^0 >= 56
 Flight_302_Capacity: t_5^0 + t_9^0 >= 82
 Flight_303_Capacity: t_15^0 >= -64
 Demand_Limit_1: t_1^0 <= 90
 Demand_Limit_2: t_2^0 + t_2^1 <= 120
 Demand_Limit_3: t_3^0 + t_3^4 <= 70
 Demand_Limit_4: t_4^0 <= 100
 Demand_Limit_5: t_5^0 <= 50
 Demand_Limit_6: t_6^0 <= 120
 Demand_Limit_7: t_7^0 <= 80
 Demand_Limit_8: t_8^0 <= 70
 Demand_Limit_9: t_9^0 <= 140
 Demand_Limit_10: t_10^0 <= 125
 Demand_Limit_11: t_11^0 <= 50
 Demand_Limit_12: t_12^0 + t_12^11 <= 180
 Demand_Limit_13: t_13^0 <= 30
 Demand_Limit_14: t_14^0 <= 75
 Demand_Limit_15: t_15^0 <= 80
Bounds
End
