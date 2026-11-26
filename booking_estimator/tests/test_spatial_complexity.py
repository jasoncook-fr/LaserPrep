import pytest
from booking_estimator.spatial_complexity import analyze_spatial_complexity
def test_grid_occupancy_and_sum():
 m={"width_mm":10,"height_mm":10,"min_x_mm":0,"min_y_mm":0,"elements":[{"length_mm":5,"min_x_mm":0,"min_y_mm":0,"width_mm":1,"height_mm":1},{"length_mm":2,"min_x_mm":9,"min_y_mm":9,"width_mm":1,"height_mm":1}]}
 r=analyze_spatial_complexity(m,2); assert r["occupied_cells"]==2; assert sum(map(sum,r["grid_length_mm"]))==pytest.approx(7)
def test_grid_validation():
 with pytest.raises(ValueError): analyze_spatial_complexity({},0)
