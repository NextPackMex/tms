
    # ============================================================
    # TOLLGURU API INTEGRATION (Smart Route)
    # ============================================================

    def action_compute_route_smart(self):
        """
        Calcula ruta, distancia y costos usando TollGuru API.
        Determina el tipo de vehículo basado en los ejes (Tracto + Remolques).
        """
        for record in self:
            try:
                # Validar origen y destino
                if not record.origin_address or not record.dest_address:
                    raise UserError(_("Debe definir direcciones de Origen y Destino completas."))
                
                # Consumir API
                api_data = record._fetch_tollguru_api()
                
                if api_data:
                    # Actualizar campos
                    updates = {}
                    summary = api_data.get('summary', {})
                    if 'distance' in summary:
                        updates['distance_km'] = summary['distance'].get('metric', 0) / 1000.0  # Meters to KM
                    if 'duration' in summary:
                        updates['duration_hours'] = summary['duration'] / 3600.0 # Seconds to Hours
                    
                    # Costos
                    costs = api_data.get('costs', {})
                    if 'fuel' in costs:
                        # Opcional: Si la API devuelve costo combustible
                        pass
                    if 'tag' in costs:
                         updates['cost_tolls'] = costs['tag']
                    elif 'cash' in costs:
                         updates['cost_tolls'] = costs['cash']
                         
                    record.write(updates)
                    
                    # Notificar al usuario
                    record.message_post(body=_("Ruta calculada con TollGuru: %s km, %s horas, $%s peajes.") % (
                        updates.get('distance_km', 0),
                        updates.get('duration_hours', 0),
                        updates.get('cost_tolls', 0)
                    ))

            except Exception as e:
                raise UserError(_("Error al calcular ruta: %s") % str(e))

    def _fetch_tollguru_api(self):
        """
        Conecta con TollGuru para obtener ruta.
        Usa mapeo dinámico de ejes para seleccionar el vehículo.
        """
        self.ensure_one()
        # Mapeo ejes -> tipo vehículo TollGuru
        # Tracto(3) + Rem1(2) + Dolly(2) + Rem2(2) = 9 ejes
        TOLLGURU_AXLES_MAP = {
            2: "2AxlesTruck",
            3: "3AxlesTruck",
            4: "4AxlesTruck",
            5: "5AxlesTruck",
            6: "6AxlesTruck",
            7: "7AxlesTruck",
            8: "8AxlesTruck",
            9: "9AxlesTruck",
        }

        # Obtener tipo dinámico, default 5 ejes si no está
        # Se usa total_axles calculado previamente (Tracto + Rem1 + Dolly + Rem2)
        vehicle_type = TOLLGURU_AXLES_MAP.get(self.total_axles, "5AxlesTruck")

        # Configuración (API Key debería estar en parámetros del sistema o compañía)
        # Por ahora asumimos una key o usamos una dummy si no está configurada,
        # pero el código debe ser funcional.
        api_key = self.env.company.tms_tollguru_api_key or 'DUMMY_KEY'
        url = "https://apis.tollguru.com/toll/v2/origin-destination-waypoints"
        
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }

        # Payload correcto con ejes dinámicos
        payload = {
            "from": {"address": self.origin_address},
            "to":   {"address": self.dest_address},
            "vehicle": {
                "type": vehicle_type,
                "weight": {
                    "value": self.vehicle_id.tms_gross_vehicle_weight or 15000, # Fallback weight
                    "unit": "kg"
                },
                "axles": self.total_axles,
                "height": {
                    "value": 4.5, # Standard height
                    "unit": "meter"
                }
            }
        }
        
        # Realizar petición (requests debe estar importado)
        import requests
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                # Log error details
                error_msg = response.text
                return None
        except Exception as e:
            raise UserError(_("Error de conexión con TollGuru: %s") % str(e))
